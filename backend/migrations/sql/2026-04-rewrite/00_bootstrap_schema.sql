--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: citext; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;


--
-- Name: EXTENSION citext; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';


--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: admission_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.admission_type AS ENUM (
    'yangi_qabul',
    'perevod'
);


--
-- Name: application_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.application_status AS ENUM (
    'topshirildi',
    'korib_chiqilmoqda',
    'qabul_qilindi',
    'rad_etildi'
);


--
-- Name: contract_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.contract_status AS ENUM (
    'draft',
    'signed',
    'cancelled',
    'completed'
);


--
-- Name: contract_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.contract_type AS ENUM (
    'two_party',
    'three_party'
);


--
-- Name: gender; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.gender AS ENUM (
    'male',
    'female'
);


--
-- Name: language; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.language AS ENUM (
    'uz',
    'ru',
    'en'
);


--
-- Name: lead_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.lead_status AS ENUM (
    'open',
    'won',
    'lost'
);


--
-- Name: otp_purpose; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.otp_purpose AS ENUM (
    'login',
    'register',
    'reset'
);


--
-- Name: party_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.party_role AS ENUM (
    'university',
    'student',
    'sponsor',
    'parent'
);


--
-- Name: payment_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.payment_status AS ENUM (
    'pending',
    'confirmed',
    'failed',
    'refunded'
);


--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'superadmin',
    'admin',
    'operator',
    'director',
    'accountant',
    'applicant'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: applicants; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applicants (
    user_id uuid NOT NULL,
    last_name character varying(100) NOT NULL,
    first_name character varying(100) NOT NULL,
    other_name character varying(100),
    birth_date date NOT NULL,
    gender public.gender NOT NULL,
    passport_series character varying(9),
    pinfl character varying(14),
    region_id uuid,
    district_id uuid,
    address text,
    nationality character varying(50) DEFAULT 'O''zbek'::character varying NOT NULL,
    additional_phone character varying(20),
    email public.citext,
    image_id uuid,
    passport_file_id uuid,
    registered_by_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    telegram_username character varying(64)
);


--
-- Name: application_status_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.application_status_history (
    application_id uuid NOT NULL,
    from_status public.application_status,
    to_status public.application_status NOT NULL,
    changed_by_id uuid NOT NULL,
    comment text,
    created_at timestamp with time zone DEFAULT '2026-04-27 13:24:21.03286+00'::timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


--
-- Name: applications; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.applications (
    application_number character varying(20) NOT NULL,
    applicant_id uuid NOT NULL,
    admission_type public.admission_type DEFAULT 'yangi_qabul'::public.admission_type NOT NULL,
    branch_id uuid NOT NULL,
    education_level_id uuid NOT NULL,
    education_form_id uuid NOT NULL,
    program_id uuid NOT NULL,
    diplom_id uuid,
    transfer_diplom_id uuid,
    course_id uuid,
    contract_file_id uuid,
    status public.application_status DEFAULT 'topshirildi'::public.application_status NOT NULL,
    submitted_at timestamp with time zone,
    reviewed_by_id uuid,
    reviewed_at timestamp with time zone,
    rejection_reason text,
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    lead_id uuid,
    lead_source_code character varying(40)
);


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    user_id uuid,
    action character varying(100) NOT NULL,
    entity_type character varying(100),
    entity_id uuid,
    changes jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamp with time zone DEFAULT '2026-04-27 13:24:21.03286+00'::timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


--
-- Name: branches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.branches (
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contract_parties; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contract_parties (
    contract_id uuid NOT NULL,
    party_role public.party_role NOT NULL,
    full_name character varying(255) NOT NULL,
    pinfl character varying(14),
    passport_series character varying(2),
    passport_number character varying(7),
    phone character varying(20),
    relationship character varying(100),
    address text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contract_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contract_settings (
    default_contract_type public.contract_type DEFAULT 'two_party'::public.contract_type NOT NULL,
    auto_generate_pdf boolean DEFAULT true NOT NULL,
    pdf_page_size character varying(10) DEFAULT 'A4'::character varying NOT NULL,
    company_name character varying(200) DEFAULT 'Xalqaro Innovatsion Universiteti'::character varying NOT NULL,
    company_address text,
    director_name character varying(100),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    company_inn character varying(20),
    director_title character varying(50) DEFAULT 'Rektor'::character varying NOT NULL
);


--
-- Name: contract_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contract_templates (
    name character varying(255) NOT NULL,
    body_two_party text,
    body_three_party text,
    type public.contract_type,
    language public.language,
    body_html text,
    variables jsonb,
    version smallint DEFAULT '1'::smallint NOT NULL,
    is_active boolean DEFAULT false NOT NULL,
    created_by_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: contracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contracts (
    contract_number character varying(50) NOT NULL,
    application_id uuid NOT NULL,
    template_id uuid NOT NULL,
    type public.contract_type NOT NULL,
    total_amount numeric(14,2) NOT NULL,
    paid_amount numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    currency character(3) DEFAULT 'UZS'::bpchar NOT NULL,
    status public.contract_status DEFAULT 'draft'::public.contract_status NOT NULL,
    signed_at timestamp with time zone,
    pdf_file_id uuid,
    created_by_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: countries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.countries (
    name character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: courses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.courses (
    name character varying(255) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dictionary_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dictionary_items (
    type_id uuid NOT NULL,
    parent_id uuid,
    code character varying(50),
    name_uz character varying(255) NOT NULL,
    name_ru character varying(255),
    name_en character varying(255),
    sort_order integer DEFAULT 0 NOT NULL,
    extra jsonb,
    is_active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: dictionary_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dictionary_types (
    code character varying(50) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    is_hierarchical boolean DEFAULT false NOT NULL,
    is_system boolean DEFAULT false NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: diploms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.diploms (
    user_id uuid NOT NULL,
    serial_number character varying(100) NOT NULL,
    education_type_id uuid NOT NULL,
    institution_type_id uuid NOT NULL,
    university_name text NOT NULL,
    graduation_year character varying(4) NOT NULL,
    region_id uuid NOT NULL,
    district_id uuid NOT NULL,
    diploma_file_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: districts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.districts (
    name character varying(100) NOT NULL,
    region_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: education_forms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.education_forms (
    name character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: education_levels; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.education_levels (
    name character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: education_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.education_types (
    name character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: educations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.educations (
    applicant_id uuid NOT NULL,
    education_level_id uuid NOT NULL,
    institution_name character varying(255) NOT NULL,
    specialty character varying(255),
    diploma_series character varying(20),
    diploma_number character varying(50),
    start_year smallint,
    end_year smallint NOT NULL,
    gpa numeric(4,2),
    is_primary boolean DEFAULT false NOT NULL,
    diploma_file_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.files (
    original_name character varying(255) NOT NULL,
    storage_path character varying(500) NOT NULL,
    mime_type character varying(100) NOT NULL,
    size_bytes bigint NOT NULL,
    uploaded_by_id uuid,
    created_at timestamp with time zone DEFAULT '2026-04-27 13:24:21.03286+00'::timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


--
-- Name: institution_types; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.institution_types (
    name character varying(100) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: lead_activities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_activities (
    lead_id uuid NOT NULL,
    user_id uuid,
    action character varying(40) NOT NULL,
    from_stage_id uuid,
    to_stage_id uuid,
    comment text,
    extra jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL
);


--
-- Name: lead_lost_reasons; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_lost_reasons (
    name character varying(120) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    order_index smallint DEFAULT '0'::smallint NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: lead_pipelines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_pipelines (
    name character varying(100) NOT NULL,
    description text,
    is_default boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    order_index smallint DEFAULT '0'::smallint NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: lead_sources; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_sources (
    code character varying(40) NOT NULL,
    name character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    order_index smallint DEFAULT '0'::smallint NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: lead_stages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lead_stages (
    pipeline_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    order_index smallint DEFAULT '0'::smallint NOT NULL,
    color character varying(20),
    is_terminal boolean DEFAULT false NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: leads; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.leads (
    full_name character varying(150) NOT NULL,
    phone character varying(20) NOT NULL,
    email character varying(120),
    pipeline_id uuid NOT NULL,
    stage_id uuid NOT NULL,
    source_id uuid,
    source_meta jsonb,
    branch_id uuid,
    program_id uuid,
    assigned_to_id uuid,
    created_by_id uuid,
    notes text,
    status public.lead_status DEFAULT 'open'::public.lead_status NOT NULL,
    applicant_id uuid,
    application_id uuid,
    converted_at timestamp with time zone,
    lost_reason_id uuid,
    lost_comment text,
    lost_at timestamp with time zone,
    last_contact_at timestamp with time zone,
    stage_entered_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    telegram_username character varying(64),
    next_contact_at timestamp with time zone,
    next_contact_note text
);


--
-- Name: otp_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.otp_codes (
    phone character varying(20) NOT NULL,
    code_hash character varying(255) NOT NULL,
    purpose public.otp_purpose NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    is_used boolean DEFAULT false NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    ip_address inet,
    created_at timestamp with time zone DEFAULT '2026-04-27 13:24:21.03286+00'::timestamp with time zone NOT NULL,
    id uuid NOT NULL
);


--
-- Name: passports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passports (
    applicant_id uuid NOT NULL,
    series character varying(2) NOT NULL,
    number character varying(7) NOT NULL,
    pinfl character varying(14) NOT NULL,
    issued_by character varying(255) NOT NULL,
    issued_date date NOT NULL,
    expires_date date NOT NULL,
    scan_file_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    payment_number character varying(50) NOT NULL,
    contract_id uuid NOT NULL,
    amount numeric(14,2) NOT NULL,
    currency character(3) DEFAULT 'UZS'::bpchar NOT NULL,
    payment_method_id uuid NOT NULL,
    status public.payment_status DEFAULT 'pending'::public.payment_status NOT NULL,
    paid_at timestamp with time zone,
    reference character varying(100),
    receipt_file_id uuid,
    registered_by_id uuid,
    notes text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.programs (
    branch_id uuid NOT NULL,
    education_level_id uuid NOT NULL,
    education_form_id uuid NOT NULL,
    name character varying(200) NOT NULL,
    code character varying(100) NOT NULL,
    image_id uuid,
    tuition_fee numeric(14,2) NOT NULL,
    contract_series character varying(100) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    study_duration_years smallint NOT NULL
);


--
-- Name: refresh_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.refresh_tokens (
    user_id uuid NOT NULL,
    token_hash character varying(255) NOT NULL,
    user_agent text,
    ip_address inet,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: regions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.regions (
    name character varying(100) NOT NULL,
    country_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: transfer_diploms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transfer_diploms (
    user_id uuid NOT NULL,
    country_id uuid NOT NULL,
    university_name text NOT NULL,
    target_course_id uuid NOT NULL,
    transcript_file_id uuid,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    phone character varying(20) NOT NULL,
    email public.citext,
    password_hash character varying(255),
    full_name character varying(255),
    role public.user_role NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_phone_verified boolean DEFAULT false NOT NULL,
    last_login_at timestamp with time zone,
    created_by_id uuid,
    deleted_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: applicants pk_applicants; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT pk_applicants PRIMARY KEY (id);


--
-- Name: application_status_history pk_application_status_history; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_status_history
    ADD CONSTRAINT pk_application_status_history PRIMARY KEY (id);


--
-- Name: applications pk_applications; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT pk_applications PRIMARY KEY (id);


--
-- Name: audit_logs pk_audit_logs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT pk_audit_logs PRIMARY KEY (id);


--
-- Name: branches pk_branches; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT pk_branches PRIMARY KEY (id);


--
-- Name: contract_parties pk_contract_parties; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_parties
    ADD CONSTRAINT pk_contract_parties PRIMARY KEY (id);


--
-- Name: contract_settings pk_contract_settings; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_settings
    ADD CONSTRAINT pk_contract_settings PRIMARY KEY (id);


--
-- Name: contract_templates pk_contract_templates; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_templates
    ADD CONSTRAINT pk_contract_templates PRIMARY KEY (id);


--
-- Name: contracts pk_contracts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT pk_contracts PRIMARY KEY (id);


--
-- Name: countries pk_countries; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT pk_countries PRIMARY KEY (id);


--
-- Name: courses pk_courses; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT pk_courses PRIMARY KEY (id);


--
-- Name: dictionary_items pk_dictionary_items; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_items
    ADD CONSTRAINT pk_dictionary_items PRIMARY KEY (id);


--
-- Name: dictionary_types pk_dictionary_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_types
    ADD CONSTRAINT pk_dictionary_types PRIMARY KEY (id);


--
-- Name: diploms pk_diploms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT pk_diploms PRIMARY KEY (id);


--
-- Name: districts pk_districts; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.districts
    ADD CONSTRAINT pk_districts PRIMARY KEY (id);


--
-- Name: education_forms pk_education_forms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_forms
    ADD CONSTRAINT pk_education_forms PRIMARY KEY (id);


--
-- Name: education_levels pk_education_levels; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_levels
    ADD CONSTRAINT pk_education_levels PRIMARY KEY (id);


--
-- Name: education_types pk_education_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_types
    ADD CONSTRAINT pk_education_types PRIMARY KEY (id);


--
-- Name: educations pk_educations; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educations
    ADD CONSTRAINT pk_educations PRIMARY KEY (id);


--
-- Name: files pk_files; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT pk_files PRIMARY KEY (id);


--
-- Name: institution_types pk_institution_types; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.institution_types
    ADD CONSTRAINT pk_institution_types PRIMARY KEY (id);


--
-- Name: lead_activities pk_lead_activities; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT pk_lead_activities PRIMARY KEY (id);


--
-- Name: lead_lost_reasons pk_lead_lost_reasons; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_lost_reasons
    ADD CONSTRAINT pk_lead_lost_reasons PRIMARY KEY (id);


--
-- Name: lead_pipelines pk_lead_pipelines; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_pipelines
    ADD CONSTRAINT pk_lead_pipelines PRIMARY KEY (id);


--
-- Name: lead_sources pk_lead_sources; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_sources
    ADD CONSTRAINT pk_lead_sources PRIMARY KEY (id);


--
-- Name: lead_stages pk_lead_stages; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_stages
    ADD CONSTRAINT pk_lead_stages PRIMARY KEY (id);


--
-- Name: leads pk_leads; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT pk_leads PRIMARY KEY (id);


--
-- Name: otp_codes pk_otp_codes; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.otp_codes
    ADD CONSTRAINT pk_otp_codes PRIMARY KEY (id);


--
-- Name: passports pk_passports; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT pk_passports PRIMARY KEY (id);


--
-- Name: payments pk_payments; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT pk_payments PRIMARY KEY (id);


--
-- Name: programs pk_programs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT pk_programs PRIMARY KEY (id);


--
-- Name: refresh_tokens pk_refresh_tokens; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT pk_refresh_tokens PRIMARY KEY (id);


--
-- Name: regions pk_regions; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT pk_regions PRIMARY KEY (id);


--
-- Name: transfer_diploms pk_transfer_diploms; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT pk_transfer_diploms PRIMARY KEY (id);


--
-- Name: users pk_users; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT pk_users PRIMARY KEY (id);


--
-- Name: applicants uq_applicants_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT uq_applicants_user_id UNIQUE (user_id);


--
-- Name: applications uq_applications_applicant_program; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT uq_applications_applicant_program UNIQUE (applicant_id, program_id);


--
-- Name: applications uq_applications_application_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT uq_applications_application_number UNIQUE (application_number);


--
-- Name: branches uq_branches_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.branches
    ADD CONSTRAINT uq_branches_name UNIQUE (name);


--
-- Name: contracts uq_contracts_contract_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT uq_contracts_contract_number UNIQUE (contract_number);


--
-- Name: countries uq_countries_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.countries
    ADD CONSTRAINT uq_countries_name UNIQUE (name);


--
-- Name: courses uq_courses_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.courses
    ADD CONSTRAINT uq_courses_name UNIQUE (name);


--
-- Name: dictionary_items uq_dictionary_items_type_id_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_items
    ADD CONSTRAINT uq_dictionary_items_type_id_code UNIQUE (type_id, code);


--
-- Name: dictionary_types uq_dictionary_types_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_types
    ADD CONSTRAINT uq_dictionary_types_code UNIQUE (code);


--
-- Name: diploms uq_diploms_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT uq_diploms_user_id UNIQUE (user_id);


--
-- Name: districts uq_districts_name_region; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.districts
    ADD CONSTRAINT uq_districts_name_region UNIQUE (name, region_id);


--
-- Name: education_forms uq_education_forms_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_forms
    ADD CONSTRAINT uq_education_forms_name UNIQUE (name);


--
-- Name: education_levels uq_education_levels_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_levels
    ADD CONSTRAINT uq_education_levels_name UNIQUE (name);


--
-- Name: education_types uq_education_types_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.education_types
    ADD CONSTRAINT uq_education_types_name UNIQUE (name);


--
-- Name: institution_types uq_institution_types_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.institution_types
    ADD CONSTRAINT uq_institution_types_name UNIQUE (name);


--
-- Name: lead_lost_reasons uq_lead_lost_reasons_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_lost_reasons
    ADD CONSTRAINT uq_lead_lost_reasons_name UNIQUE (name);


--
-- Name: lead_pipelines uq_lead_pipelines_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_pipelines
    ADD CONSTRAINT uq_lead_pipelines_name UNIQUE (name);


--
-- Name: lead_sources uq_lead_sources_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_sources
    ADD CONSTRAINT uq_lead_sources_code UNIQUE (code);


--
-- Name: lead_stages uq_lead_stages_pipeline_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_stages
    ADD CONSTRAINT uq_lead_stages_pipeline_name UNIQUE (pipeline_id, name);


--
-- Name: passports uq_passports_applicant_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT uq_passports_applicant_id UNIQUE (applicant_id);


--
-- Name: passports uq_passports_pinfl; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT uq_passports_pinfl UNIQUE (pinfl);


--
-- Name: passports uq_passports_series_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT uq_passports_series_number UNIQUE (series, number);


--
-- Name: payments uq_payments_payment_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT uq_payments_payment_number UNIQUE (payment_number);


--
-- Name: refresh_tokens uq_refresh_tokens_token_hash; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT uq_refresh_tokens_token_hash UNIQUE (token_hash);


--
-- Name: regions uq_regions_name_country; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT uq_regions_name_country UNIQUE (name, country_id);


--
-- Name: transfer_diploms uq_transfer_diploms_user_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT uq_transfer_diploms_user_id UNIQUE (user_id);


--
-- Name: users uq_users_email; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT uq_users_email UNIQUE (email);


--
-- Name: ix_applicants_passport_series; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_applicants_passport_series ON public.applicants USING btree (passport_series);


--
-- Name: ix_applicants_pinfl; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_applicants_pinfl ON public.applicants USING btree (pinfl);


--
-- Name: ix_applicants_region_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applicants_region_id ON public.applicants USING btree (region_id);


--
-- Name: ix_application_status_history_application_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_application_status_history_application_id ON public.application_status_history USING btree (application_id);


--
-- Name: ix_application_status_history_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_application_status_history_created_at ON public.application_status_history USING btree (created_at);


--
-- Name: ix_applications_admission_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_admission_type ON public.applications USING btree (admission_type);


--
-- Name: ix_applications_applicant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_applicant_id ON public.applications USING btree (applicant_id);


--
-- Name: ix_applications_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_branch_id ON public.applications USING btree (branch_id);


--
-- Name: ix_applications_lead_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_lead_id ON public.applications USING btree (lead_id);


--
-- Name: ix_applications_program_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_program_id ON public.applications USING btree (program_id);


--
-- Name: ix_applications_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_applications_status ON public.applications USING btree (status);


--
-- Name: ix_audit_logs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_created_at ON public.audit_logs USING btree (created_at);


--
-- Name: ix_audit_logs_entity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_entity ON public.audit_logs USING btree (entity_type, entity_id);


--
-- Name: ix_audit_logs_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_logs_user_id ON public.audit_logs USING btree (user_id);


--
-- Name: ix_contract_parties_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contract_parties_contract_id ON public.contract_parties USING btree (contract_id);


--
-- Name: ix_contracts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contracts_status ON public.contracts USING btree (status);


--
-- Name: ix_dictionary_items_parent_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dictionary_items_parent_id ON public.dictionary_items USING btree (parent_id);


--
-- Name: ix_dictionary_items_type_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dictionary_items_type_id ON public.dictionary_items USING btree (type_id);


--
-- Name: ix_districts_region_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_districts_region_id ON public.districts USING btree (region_id);


--
-- Name: ix_educations_applicant_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_educations_applicant_id ON public.educations USING btree (applicant_id);


--
-- Name: ix_educations_end_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_educations_end_year ON public.educations USING btree (end_year);


--
-- Name: ix_lead_activities_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_activities_created_at ON public.lead_activities USING btree (created_at);


--
-- Name: ix_lead_activities_lead_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_activities_lead_created ON public.lead_activities USING btree (lead_id, created_at);


--
-- Name: ix_lead_stages_pipeline_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_stages_pipeline_id ON public.lead_stages USING btree (pipeline_id);


--
-- Name: ix_lead_stages_pipeline_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lead_stages_pipeline_order ON public.lead_stages USING btree (pipeline_id, order_index);


--
-- Name: ix_leads_assigned; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_assigned ON public.leads USING btree (assigned_to_id);


--
-- Name: ix_leads_next_contact_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_next_contact_at ON public.leads USING btree (next_contact_at);


--
-- Name: ix_leads_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_phone ON public.leads USING btree (phone);


--
-- Name: ix_leads_pipeline_stage; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_pipeline_stage ON public.leads USING btree (pipeline_id, stage_id);


--
-- Name: ix_leads_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_leads_status ON public.leads USING btree (status);


--
-- Name: ix_otp_codes_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_otp_codes_expires_at ON public.otp_codes USING btree (expires_at);


--
-- Name: ix_otp_codes_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_otp_codes_phone ON public.otp_codes USING btree (phone);


--
-- Name: ix_payments_contract_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_contract_id ON public.payments USING btree (contract_id);


--
-- Name: ix_payments_paid_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_paid_at ON public.payments USING btree (paid_at);


--
-- Name: ix_payments_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_payments_status ON public.payments USING btree (status);


--
-- Name: ix_programs_branch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_programs_branch_id ON public.programs USING btree (branch_id);


--
-- Name: ix_programs_education_form_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_programs_education_form_id ON public.programs USING btree (education_form_id);


--
-- Name: ix_programs_education_level_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_programs_education_level_id ON public.programs USING btree (education_level_id);


--
-- Name: ix_programs_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_programs_is_active ON public.programs USING btree (is_active);


--
-- Name: ix_refresh_tokens_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_refresh_tokens_user_id ON public.refresh_tokens USING btree (user_id);


--
-- Name: ix_regions_country_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_regions_country_id ON public.regions USING btree (country_id);


--
-- Name: ix_users_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_is_active ON public.users USING btree (is_active);


--
-- Name: ix_users_phone; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_phone ON public.users USING btree (phone);


--
-- Name: ix_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_role ON public.users USING btree (role);


--
-- Name: uq_contracts_application_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_contracts_application_active ON public.contracts USING btree (application_id) WHERE (status <> 'cancelled'::public.contract_status);


--
-- Name: applications applications_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_district_id_districts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_district_id_districts FOREIGN KEY (district_id) REFERENCES public.districts(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_image_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_image_id_files FOREIGN KEY (image_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_passport_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_passport_file_id_files FOREIGN KEY (passport_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_region_id_regions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_region_id_regions FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_registered_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_registered_by_id_users FOREIGN KEY (registered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: applicants fk_applicants_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applicants
    ADD CONSTRAINT fk_applicants_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: application_status_history fk_application_status_history_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_status_history
    ADD CONSTRAINT fk_application_status_history_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE CASCADE;


--
-- Name: application_status_history fk_application_status_history_changed_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.application_status_history
    ADD CONSTRAINT fk_application_status_history_changed_by_id_users FOREIGN KEY (changed_by_id) REFERENCES public.users(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_applicant_id_applicants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_applicant_id_applicants FOREIGN KEY (applicant_id) REFERENCES public.applicants(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_branch_id_branches; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_branch_id_branches FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_contract_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_contract_file_id_files FOREIGN KEY (contract_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: applications fk_applications_course_id_courses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_course_id_courses FOREIGN KEY (course_id) REFERENCES public.courses(id) ON DELETE SET NULL;


--
-- Name: applications fk_applications_diplom_id_diploms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_diplom_id_diploms FOREIGN KEY (diplom_id) REFERENCES public.diploms(id) ON DELETE SET NULL;


--
-- Name: applications fk_applications_education_form_id_education_forms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_education_form_id_education_forms FOREIGN KEY (education_form_id) REFERENCES public.education_forms(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_education_level_id_education_levels; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_education_level_id_education_levels FOREIGN KEY (education_level_id) REFERENCES public.education_levels(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_program_id_programs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_program_id_programs FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE RESTRICT;


--
-- Name: applications fk_applications_reviewed_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_reviewed_by_id_users FOREIGN KEY (reviewed_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: applications fk_applications_transfer_diplom_id_transfer_diploms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT fk_applications_transfer_diplom_id_transfer_diploms FOREIGN KEY (transfer_diplom_id) REFERENCES public.transfer_diploms(id) ON DELETE SET NULL;


--
-- Name: audit_logs fk_audit_logs_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT fk_audit_logs_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: contract_parties fk_contract_parties_contract_id_contracts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_parties
    ADD CONSTRAINT fk_contract_parties_contract_id_contracts FOREIGN KEY (contract_id) REFERENCES public.contracts(id) ON DELETE CASCADE;


--
-- Name: contract_templates fk_contract_templates_created_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contract_templates
    ADD CONSTRAINT fk_contract_templates_created_by_id_users FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: contracts fk_contracts_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT fk_contracts_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE RESTRICT;


--
-- Name: contracts fk_contracts_created_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT fk_contracts_created_by_id_users FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: contracts fk_contracts_pdf_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT fk_contracts_pdf_file_id_files FOREIGN KEY (pdf_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: contracts fk_contracts_template_id_contract_templates; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT fk_contracts_template_id_contract_templates FOREIGN KEY (template_id) REFERENCES public.contract_templates(id) ON DELETE RESTRICT;


--
-- Name: dictionary_items fk_dictionary_items_parent_id_dictionary_items; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_items
    ADD CONSTRAINT fk_dictionary_items_parent_id_dictionary_items FOREIGN KEY (parent_id) REFERENCES public.dictionary_items(id) ON DELETE CASCADE;


--
-- Name: dictionary_items fk_dictionary_items_type_id_dictionary_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dictionary_items
    ADD CONSTRAINT fk_dictionary_items_type_id_dictionary_types FOREIGN KEY (type_id) REFERENCES public.dictionary_types(id) ON DELETE CASCADE;


--
-- Name: diploms fk_diploms_diploma_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_diploma_file_id_files FOREIGN KEY (diploma_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: diploms fk_diploms_district_id_districts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_district_id_districts FOREIGN KEY (district_id) REFERENCES public.districts(id) ON DELETE RESTRICT;


--
-- Name: diploms fk_diploms_education_type_id_education_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_education_type_id_education_types FOREIGN KEY (education_type_id) REFERENCES public.education_types(id) ON DELETE RESTRICT;


--
-- Name: diploms fk_diploms_institution_type_id_institution_types; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_institution_type_id_institution_types FOREIGN KEY (institution_type_id) REFERENCES public.institution_types(id) ON DELETE RESTRICT;


--
-- Name: diploms fk_diploms_region_id_regions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_region_id_regions FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE RESTRICT;


--
-- Name: diploms fk_diploms_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.diploms
    ADD CONSTRAINT fk_diploms_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: districts fk_districts_region_id_regions; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.districts
    ADD CONSTRAINT fk_districts_region_id_regions FOREIGN KEY (region_id) REFERENCES public.regions(id) ON DELETE RESTRICT;


--
-- Name: educations fk_educations_applicant_id_applicants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educations
    ADD CONSTRAINT fk_educations_applicant_id_applicants FOREIGN KEY (applicant_id) REFERENCES public.applicants(id) ON DELETE CASCADE;


--
-- Name: educations fk_educations_diploma_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educations
    ADD CONSTRAINT fk_educations_diploma_file_id_files FOREIGN KEY (diploma_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: educations fk_educations_education_level_id_dictionary_items; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.educations
    ADD CONSTRAINT fk_educations_education_level_id_dictionary_items FOREIGN KEY (education_level_id) REFERENCES public.dictionary_items(id) ON DELETE RESTRICT;


--
-- Name: files fk_files_uploaded_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT fk_files_uploaded_by_id_users FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: lead_activities fk_lead_activities_from_stage_id_lead_stages; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT fk_lead_activities_from_stage_id_lead_stages FOREIGN KEY (from_stage_id) REFERENCES public.lead_stages(id) ON DELETE SET NULL;


--
-- Name: lead_activities fk_lead_activities_lead_id_leads; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT fk_lead_activities_lead_id_leads FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE CASCADE;


--
-- Name: lead_activities fk_lead_activities_to_stage_id_lead_stages; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT fk_lead_activities_to_stage_id_lead_stages FOREIGN KEY (to_stage_id) REFERENCES public.lead_stages(id) ON DELETE SET NULL;


--
-- Name: lead_activities fk_lead_activities_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT fk_lead_activities_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: lead_stages fk_lead_stages_pipeline_id_lead_pipelines; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lead_stages
    ADD CONSTRAINT fk_lead_stages_pipeline_id_lead_pipelines FOREIGN KEY (pipeline_id) REFERENCES public.lead_pipelines(id) ON DELETE CASCADE;


--
-- Name: leads fk_leads_applicant_id_applicants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_applicant_id_applicants FOREIGN KEY (applicant_id) REFERENCES public.applicants(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_application_id_applications; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_application_id_applications FOREIGN KEY (application_id) REFERENCES public.applications(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_assigned_to_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_assigned_to_id_users FOREIGN KEY (assigned_to_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_branch_id_branches; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_branch_id_branches FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_created_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_created_by_id_users FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_lost_reason_id_lead_lost_reasons; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_lost_reason_id_lead_lost_reasons FOREIGN KEY (lost_reason_id) REFERENCES public.lead_lost_reasons(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_pipeline_id_lead_pipelines; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_pipeline_id_lead_pipelines FOREIGN KEY (pipeline_id) REFERENCES public.lead_pipelines(id) ON DELETE RESTRICT;


--
-- Name: leads fk_leads_program_id_programs; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_program_id_programs FOREIGN KEY (program_id) REFERENCES public.programs(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_source_id_lead_sources; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_source_id_lead_sources FOREIGN KEY (source_id) REFERENCES public.lead_sources(id) ON DELETE SET NULL;


--
-- Name: leads fk_leads_stage_id_lead_stages; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT fk_leads_stage_id_lead_stages FOREIGN KEY (stage_id) REFERENCES public.lead_stages(id) ON DELETE RESTRICT;


--
-- Name: passports fk_passports_applicant_id_applicants; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT fk_passports_applicant_id_applicants FOREIGN KEY (applicant_id) REFERENCES public.applicants(id) ON DELETE CASCADE;


--
-- Name: passports fk_passports_scan_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passports
    ADD CONSTRAINT fk_passports_scan_file_id_files FOREIGN KEY (scan_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: payments fk_payments_contract_id_contracts; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_contract_id_contracts FOREIGN KEY (contract_id) REFERENCES public.contracts(id) ON DELETE RESTRICT;


--
-- Name: payments fk_payments_payment_method_id_dictionary_items; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_payment_method_id_dictionary_items FOREIGN KEY (payment_method_id) REFERENCES public.dictionary_items(id) ON DELETE RESTRICT;


--
-- Name: payments fk_payments_receipt_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_receipt_file_id_files FOREIGN KEY (receipt_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: payments fk_payments_registered_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payments_registered_by_id_users FOREIGN KEY (registered_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: programs fk_programs_branch_id_branches; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT fk_programs_branch_id_branches FOREIGN KEY (branch_id) REFERENCES public.branches(id) ON DELETE RESTRICT;


--
-- Name: programs fk_programs_education_form_id_education_forms; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT fk_programs_education_form_id_education_forms FOREIGN KEY (education_form_id) REFERENCES public.education_forms(id) ON DELETE RESTRICT;


--
-- Name: programs fk_programs_education_level_id_education_levels; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT fk_programs_education_level_id_education_levels FOREIGN KEY (education_level_id) REFERENCES public.education_levels(id) ON DELETE RESTRICT;


--
-- Name: programs fk_programs_image_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.programs
    ADD CONSTRAINT fk_programs_image_id_files FOREIGN KEY (image_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: refresh_tokens fk_refresh_tokens_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.refresh_tokens
    ADD CONSTRAINT fk_refresh_tokens_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: regions fk_regions_country_id_countries; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.regions
    ADD CONSTRAINT fk_regions_country_id_countries FOREIGN KEY (country_id) REFERENCES public.countries(id) ON DELETE RESTRICT;


--
-- Name: transfer_diploms fk_transfer_diploms_country_id_countries; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT fk_transfer_diploms_country_id_countries FOREIGN KEY (country_id) REFERENCES public.countries(id) ON DELETE RESTRICT;


--
-- Name: transfer_diploms fk_transfer_diploms_target_course_id_courses; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT fk_transfer_diploms_target_course_id_courses FOREIGN KEY (target_course_id) REFERENCES public.courses(id) ON DELETE RESTRICT;


--
-- Name: transfer_diploms fk_transfer_diploms_transcript_file_id_files; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT fk_transfer_diploms_transcript_file_id_files FOREIGN KEY (transcript_file_id) REFERENCES public.files(id) ON DELETE SET NULL;


--
-- Name: transfer_diploms fk_transfer_diploms_user_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transfer_diploms
    ADD CONSTRAINT fk_transfer_diploms_user_id_users FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users fk_users_created_by_id_users; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT fk_users_created_by_id_users FOREIGN KEY (created_by_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--



-- ==========================================================
-- Add server-side UUID defaults to all `id` columns.
-- Required because the SQLAlchemy ORM generates UUIDs in Python,
-- so the dumped schema has no DB-side default. Raw INSERTs (seeds)
-- need a default to avoid "null value in column id" errors.

-- ==========================================================
-- Add server-side UUID defaults to all `id` columns.
-- Required because the SQLAlchemy ORM generates UUIDs in Python,
-- so the dumped schema has no DB-side default. Raw INSERTs (seeds)
-- need a default to avoid "null value in column id" errors.
-- ==========================================================
SET search_path = public;

DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN
        SELECT table_name FROM information_schema.columns
        WHERE column_name = 'id' AND data_type = 'uuid'
          AND table_schema = 'public'
          AND column_default IS NULL
    LOOP
        EXECUTE format('ALTER TABLE public.%I ALTER COLUMN id SET DEFAULT uuid_generate_v4()', r.table_name);
    END LOOP;
END $$;
