"""Bulk-regenerate contract PDFs after a template fix.

Context: the bank-account block in contract template
``f5887f18-9c07-47e3-8137-6c4ca4dbf034`` was wrong. Template body has
been corrected (Ipak Yo'li reqs), but every contract already issued
against that template still points at a PDF rendered from the OLD
body. This script re-renders every affected contract's PDF in place
using the *current* template body and swaps ``contract.pdf_file_id``
to the new file row. Old File rows are left orphaned (NOT deleted) —
they can be vacuumed later if disk pressure becomes a concern.

Usage on the server (inside the backend container):

    # 1) Dry-run — print the candidate list, render nothing:
    docker compose exec backend python -m scripts.regenerate_contract_pdfs \\
        --template-id f5887f18-9c07-47e3-8137-6c4ca4dbf034 --dry-run

    # 2) Real run, default scope (signed + draft, skip cancelled/completed):
    docker compose exec backend python -m scripts.regenerate_contract_pdfs \\
        --template-id f5887f18-9c07-47e3-8137-6c4ca4dbf034

    # 3) Limit to N for a first careful pass:
    docker compose exec backend python -m scripts.regenerate_contract_pdfs \\
        --template-id f5887f18-9c07-47e3-8137-6c4ca4dbf034 --limit 5

Flags:
    --template-id UUID  Required. Only contracts pointing at THIS template are touched.
    --dry-run           List candidates, render nothing, exit 0.
    --include-cancelled Also regenerate cancelled/completed contracts (default: skip).
    --include-unpdfed   Also generate for contracts with pdf_file_id IS NULL
                        (default: only contracts that already had a PDF — i.e. the
                        ones the customer signed against the wrong reqs).
    --limit N           Stop after N successful renders. Useful for first careful pass.
    --actor-id UUID     Stamp new file.uploaded_by_id with this user. Defaults to
                        the first superadmin found in the users table.

Safety:
    - Per-contract commit. A render failure on contract #57 doesn't
      roll back #1..#56.
    - Old File row is NOT deleted — pdf_file_id is just repointed.
      To clean up later, run a vacuum job on files not referenced
      anywhere.
    - Idempotent shape: re-running picks up everything matching the
      filter again. If you ran a partial batch, restart with the same
      command — already-regenerated rows just get re-regenerated, no
      harm done (same template body, same context → same PDF).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.enums import ContractStatus, UserRole
from app.db.session import async_session_factory

# Register all models for SQLAlchemy.
import app.db.models_registry  # noqa: F401

from app.modules.contracts.models import Contract
from app.modules.contracts.service import ContractsService
from app.modules.users.models import User

logger = get_logger("regenerate_contract_pdfs")


async def _resolve_actor_id(session, explicit: UUID | None) -> UUID:
    """Pick a user id to stamp on the new file row's uploaded_by_id."""
    if explicit is not None:
        return explicit
    row = await session.execute(
        select(User.id)
        .where(User.role == UserRole.SUPERADMIN)
        .order_by(User.created_at.asc())
        .limit(1)
    )
    actor = row.scalar_one_or_none()
    if actor is None:
        raise SystemExit(
            "No superadmin found — pass --actor-id explicitly with the UUID of "
            "the user to stamp on the new file rows."
        )
    return actor


async def _candidates(session, template_id: UUID, *, include_cancelled: bool, include_unpdfed: bool) -> list[Contract]:
    stmt = select(Contract).where(Contract.template_id == template_id)
    if not include_cancelled:
        stmt = stmt.where(
            Contract.status.notin_([ContractStatus.CANCELLED, ContractStatus.COMPLETED])
        )
    if not include_unpdfed:
        stmt = stmt.where(Contract.pdf_file_id.isnot(None))
    stmt = stmt.order_by(Contract.created_at.asc())
    return (await session.execute(stmt)).scalars().all()


async def _regenerate_one(contract_id: UUID, *, actor_id: UUID) -> tuple[bool, str]:
    """Open a fresh session per contract so each commit is independent."""
    async with async_session_factory() as session:
        async with session.begin():
            svc = ContractsService(session)

            contract = await svc.contracts.get(contract_id)
            if contract is None:
                return False, "contract vanished mid-run"

            # Fetch every dependency _render_and_attach_pdf needs.
            application = await svc.applications.get(contract.application_id)
            if application is None:
                return False, "application missing"
            applicant = await svc.applicants.get(application.applicant_id)
            if applicant is None:
                return False, "applicant missing"
            program = await svc.programs.get(application.program_id)
            if program is None:
                return False, "program missing"
            template = await svc.get_template(contract.template_id)

            old_pdf = contract.pdf_file_id

            await svc._render_and_attach_pdf(
                contract=contract,
                template=template,
                applicant=applicant,
                application=application,
                program=program,
                actor_id=actor_id,
            )

            new_pdf = contract.pdf_file_id
            if new_pdf == old_pdf or new_pdf is None:
                return False, "render produced no new file (check backend logs for contract.pdf_failed)"

            return True, f"{old_pdf} → {new_pdf}"


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--template-id", required=True, type=UUID,
                        help="UUID of the fixed template (only its contracts get regenerated).")
    parser.add_argument("--dry-run", action="store_true",
                        help="List candidates only, render nothing.")
    parser.add_argument("--include-cancelled", action="store_true",
                        help="Also regenerate cancelled/completed contracts.")
    parser.add_argument("--include-unpdfed", action="store_true",
                        help="Also generate for contracts that never had a PDF.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Stop after N successful renders.")
    parser.add_argument("--actor-id", type=UUID, default=None,
                        help="User UUID to stamp on the new file row; defaults to oldest superadmin.")
    args = parser.parse_args()

    configure_logging(debug=False)

    async with async_session_factory() as session:
        actor_id = await _resolve_actor_id(session, args.actor_id)
        rows = await _candidates(
            session,
            args.template_id,
            include_cancelled=args.include_cancelled,
            include_unpdfed=args.include_unpdfed,
        )

    print("=" * 72)
    print(f"Template:           {args.template_id}")
    print(f"Actor (uploaded_by):{actor_id}")
    print(f"Include cancelled:  {args.include_cancelled}")
    print(f"Include unpdfed:    {args.include_unpdfed}")
    print(f"Candidates:         {len(rows)}")
    if args.limit is not None:
        print(f"Limit:              {args.limit}")
    print("=" * 72)

    if not rows:
        print("Nothing to do.")
        return

    if args.dry_run:
        for c in rows[: args.limit or len(rows)]:
            print(f"  {c.contract_number:<24}  {c.status.value:<10}  {c.id}  pdf={c.pdf_file_id}")
        print()
        print(f"Dry-run only — {min(len(rows), args.limit or len(rows))} contracts would be regenerated.")
        return

    ok = 0
    failed: list[tuple[UUID, str, str]] = []
    for idx, c in enumerate(rows, start=1):
        if args.limit is not None and ok >= args.limit:
            break
        try:
            success, detail = await _regenerate_one(c.id, actor_id=actor_id)
        except Exception as exc:
            success, detail = False, f"{type(exc).__name__}: {exc}"
        if success:
            ok += 1
            print(f"[{idx:>4}/{len(rows)}] OK   {c.contract_number:<24}  {detail}")
        else:
            failed.append((c.id, c.contract_number, detail))
            print(f"[{idx:>4}/{len(rows)}] FAIL {c.contract_number:<24}  {detail}", file=sys.stderr)

    print()
    print("=" * 72)
    print(f"Regenerated:  {ok}")
    print(f"Failed:       {len(failed)}")
    if failed:
        print()
        print("Failures:")
        for cid, num, why in failed:
            print(f"  {num:<24}  {cid}  {why}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
