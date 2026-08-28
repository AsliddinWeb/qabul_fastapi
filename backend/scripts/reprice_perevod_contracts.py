"""Reprice perevod (transfer) contracts + set Sirtqi program prices.

Business change: o'qishni ko'chirish (transfer) students pay a flat amount
(default 14 000 000). A contract carries a SNAPSHOT ``total_amount`` (the
program price at creation time) and the PDF renders THAT number — so fixing
existing contracts means updating ``total_amount`` AND re-rendering the PDF.
Two independent actions, both honoring --dry-run:

  1. Perevod contracts  — application.admission_type = 'perevod', status in
     (draft, signed): set total_amount = AMOUNT and re-render the PDF.
     External/billing contracts (no template) are skipped — their PDF is an
     uploaded state document we can't re-render.

  2. Sirtqi programs (--set-sirtqi) — every program whose education form name
     contains "sirtq": set tuition_fee = AMOUNT. Affects FUTURE contracts only.

Usage (inside the backend container):

    # Dry-run — show what WOULD change, touch nothing:
    python -m scripts.reprice_perevod_contracts --dry-run --set-sirtqi

    # Real run — reprice perevod contracts only:
    python -m scripts.reprice_perevod_contracts

    # Real run — reprice perevod contracts AND set Sirtqi program prices:
    python -m scripts.reprice_perevod_contracts --set-sirtqi

    # Custom amount / first careful pass:
    python -m scripts.reprice_perevod_contracts --amount 14000000 --limit 5 --dry-run

Safety:
  - Per-contract commit: a render failure on #57 doesn't roll back #1..#56.
  - Old File rows are left orphaned (pdf_file_id repointed), not deleted.
  - --dry-run changes nothing.
"""

from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update

import app.db.models_registry  # noqa: F401  (register all model tables)
from app.db.enums import AdmissionType, ContractStatus
from app.db.session import async_session_factory
from app.modules.applications.models import Application
from app.modules.contracts.models import Contract
from app.modules.contracts.service import ContractsService
from app.modules.programs.models import EducationForm, Program
from app.modules.users.models import User

DEFAULT_AMOUNT = Decimal("14000000")


async def _resolve_actor_id(session, explicit: UUID | None) -> UUID:
    if explicit:
        return explicit
    from app.db.enums import UserRole
    uid = await session.scalar(
        select(User.id).where(User.role == UserRole.SUPERADMIN).order_by(User.created_at).limit(1)
    )
    if not uid:
        raise SystemExit("No superadmin found — pass --actor-id explicitly.")
    return uid


async def _perevod_candidates(session) -> list[Contract]:
    stmt = (
        select(Contract)
        .join(Application, Application.id == Contract.application_id)
        .where(
            Application.admission_type == AdmissionType.TRANSFER,
            Contract.status.in_([ContractStatus.DRAFT, ContractStatus.SIGNED]),
            Contract.template_id.isnot(None),  # skip external/billing (no template)
        )
        .order_by(Contract.created_at)
    )
    return list((await session.scalars(stmt)).all())


async def _reprice_one(contract_id: UUID, *, amount: Decimal, actor_id: UUID) -> tuple[bool, str]:
    async with async_session_factory() as session:
        async with session.begin():
            svc = ContractsService(session)
            contract = await svc.contracts.get(contract_id)
            if contract is None:
                return False, "contract vanished mid-run"
            if contract.template_id is None:
                return False, "external/billing (no template) — skipped"

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

            old_amount = contract.total_amount
            old_pdf = contract.pdf_file_id

            contract.total_amount = amount
            await session.flush()

            await svc._render_and_attach_pdf(
                contract=contract,
                template=template,
                applicant=applicant,
                application=application,
                program=program,
                actor_id=actor_id,
            )
            new_pdf = contract.pdf_file_id
            pdf_note = (
                f"pdf {old_pdf} → {new_pdf}"
                if new_pdf and new_pdf != old_pdf
                else "PDF NOT re-rendered (check logs)"
            )
            return True, f"amount {old_amount} → {amount}; {pdf_note}"


async def _set_sirtqi_programs(amount: Decimal, *, dry_run: bool) -> None:
    async with async_session_factory() as session:
        forms = (
            await session.execute(
                select(EducationForm.id, EducationForm.name).where(EducationForm.name.ilike("%sirtq%"))
            )
        ).all()
        if not forms:
            print("  No 'Sirtqi' education form found — nothing to do.")
            return
        form_ids = [f.id for f in forms]
        print(f"  Sirtqi forms: {[f.name for f in forms]}")
        progs = (
            await session.execute(
                select(Program.id, Program.name, Program.tuition_fee).where(
                    Program.education_form_id.in_(form_ids)
                )
            )
        ).all()
        print(f"  {len(progs)} Sirtqi program(s):")
        for p in progs:
            mark = "=" if p.tuition_fee == amount else "→"
            print(f"    {p.name[:44]:<44} {p.tuition_fee} {mark} {amount}")
        if dry_run:
            print("  (dry-run — programs NOT changed)")
            return
        await session.execute(
            update(Program).where(Program.education_form_id.in_(form_ids)).values(tuition_fee=amount)
        )
        await session.commit()
        print(f"  ✓ {len(progs)} Sirtqi program(s) set to {amount}.")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--amount", type=Decimal, default=DEFAULT_AMOUNT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--set-sirtqi", action="store_true", help="Also set Sirtqi program tuition_fee.")
    parser.add_argument("--limit", type=int, default=None, help="Stop after N repriced contracts.")
    parser.add_argument("--actor-id", type=UUID, default=None)
    args = parser.parse_args()

    print(f"Amount:   {args.amount}")
    print(f"Dry-run:  {args.dry_run}")
    print("=" * 60)

    # ---- Action 2: Sirtqi program prices (future contracts) ----
    if args.set_sirtqi:
        print("Sirtqi programs (tuition_fee → future contracts):")
        await _set_sirtqi_programs(args.amount, dry_run=args.dry_run)
        print("=" * 60)

    # ---- Action 1: perevod contract repricing (existing) ----
    async with async_session_factory() as session:
        actor_id = await _resolve_actor_id(session, args.actor_id)
        candidates = await _perevod_candidates(session)

    print(f"Perevod contracts (draft/signed, system-rendered): {len(candidates)}")
    for c in candidates:
        print(f"  {c.contract_number:<24} {c.status.value:<8} {c.total_amount:>14} → {args.amount}   {c.id}")

    if args.dry_run:
        print("\n(dry-run — contracts NOT changed)")
        return
    if not candidates:
        print("\nNothing to reprice.")
        return

    print(f"\nRepricing (actor {actor_id})…")
    ok = fail = 0
    for c in candidates:
        success, msg = await _reprice_one(c.id, amount=args.amount, actor_id=actor_id)
        flag = "✓" if success else "✗"
        print(f"  {flag} {c.contract_number:<24} {msg}")
        ok += int(success)
        fail += int(not success)
        if args.limit and ok >= args.limit:
            print(f"  … stopped after {ok} (--limit).")
            break
    print(f"\nDone: {ok} repriced, {fail} skipped/failed.")


if __name__ == "__main__":
    asyncio.run(main())
