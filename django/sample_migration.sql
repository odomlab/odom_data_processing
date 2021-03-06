-- This migration script needs to run cleanly against a current dump
-- of the repository database; only then is it ready to be used in
-- production.

-- We'll do this in one or more transaction blocks.
BEGIN; -- Preamble to fix inconsistencies in the current data set.

-- Fix some inconsistencies in current sample annotation.

-- Every library now needs a sample. We set missing values to be
-- identical to the library code for the sake of having something
-- here.
update library set individual=code where (individual is null or individual='');

COMMIT;

BEGIN; -- the business of table creation and migration of the data.

-- Create sample table using optional fields for strain, sex,
-- tissue. This code generated by creating an empty database on my
-- test machine and running "python manage.py syncdb" using the
-- updated model code. The resulting pg_dump output can be used to
-- check that we're making the right changes later on as well.
--
-- Name: sample; Type: TABLE; Schema: public; Owner: chipseq; Tablespace: 
--

CREATE TABLE sample (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    tissue_id integer NOT NULL,
    source_id integer NOT NULL,
    tumour_grading_id integer,
    comment text
);

ALTER TABLE sample OWNER TO chipseq;
CREATE SEQUENCE sample_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE sample_id_seq OWNER TO chipseq;
ALTER SEQUENCE sample_id_seq OWNED BY sample.id;

CREATE TABLE source (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    strain_id integer,
    sex_id integer,
    date_of_birth date,
    date_of_death date,
    mother_id integer,
    father_id integer,
    comment text
);

ALTER TABLE source OWNER TO chipseq;
CREATE SEQUENCE source_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE source_id_seq OWNER TO chipseq;
ALTER SEQUENCE source_id_seq OWNED BY source.id;

CREATE TABLE source_treatment (
    id integer NOT NULL,
    source_id integer NOT NULL,
    date date NOT NULL,
    agent_id integer NOT NULL,
    dose character varying(128),
    dose_unit_id integer
);

ALTER TABLE source_treatment OWNER TO chipseq;
CREATE SEQUENCE source_treatment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE source_treatment_id_seq OWNER TO chipseq;
ALTER SEQUENCE source_treatment_id_seq OWNED BY source_treatment.id;

CREATE TABLE dose_unit (
    id integer NOT NULL,
    name character varying(32) NOT NULL,
    description character varying(128) NOT NULL
);

ALTER TABLE dose_unit OWNER TO chipseq;
CREATE SEQUENCE dose_unit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE dose_unit_id_seq OWNER TO chipseq;
ALTER SEQUENCE dose_unit_id_seq OWNED BY dose_unit.id;

CREATE TABLE treatment_agent (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    description character varying(256) NOT NULL,
    accession character varying(32) NOT NULL
);

ALTER TABLE treatment_agent OWNER TO chipseq;
CREATE SEQUENCE treatment_agent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE treatment_agent_id_seq OWNER TO chipseq;
ALTER SEQUENCE treatment_agent_id_seq OWNED BY treatment_agent.id;

CREATE TABLE tumour_grading (
    id integer NOT NULL,
    name character varying(64) NOT NULL,
    description character varying(256) NOT NULL
);

ALTER TABLE tumour_grading OWNER TO chipseq;
CREATE SEQUENCE tumour_grading_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER TABLE tumour_grading_id_seq OWNER TO chipseq;
ALTER SEQUENCE tumour_grading_id_seq OWNED BY tumour_grading.id;

-- This is manually added to allow our backups to run smoothly.
GRANT SELECT ON TABLE sample TO backup;
GRANT SELECT ON TABLE sample TO readonly;
GRANT SELECT ON TABLE sample_id_seq TO backup;
GRANT SELECT ON TABLE sample_id_seq TO readonly;

GRANT SELECT ON TABLE source TO backup;
GRANT SELECT ON TABLE source TO readonly;
GRANT SELECT ON TABLE source_id_seq TO backup;
GRANT SELECT ON TABLE source_id_seq TO readonly;

GRANT SELECT ON TABLE source_treatment TO backup;
GRANT SELECT ON TABLE source_treatment TO readonly;
GRANT SELECT ON TABLE source_treatment_id_seq TO backup;
GRANT SELECT ON TABLE source_treatment_id_seq TO readonly;

GRANT SELECT ON TABLE dose_unit TO backup;
GRANT SELECT ON TABLE dose_unit TO readonly;
GRANT SELECT ON TABLE dose_unit_id_seq TO backup;
GRANT SELECT ON TABLE dose_unit_id_seq TO readonly;

GRANT SELECT ON TABLE treatment_agent TO backup;
GRANT SELECT ON TABLE treatment_agent TO readonly;
GRANT SELECT ON TABLE treatment_agent_id_seq TO backup;
GRANT SELECT ON TABLE treatment_agent_id_seq TO readonly;

GRANT SELECT ON TABLE tumour_grading TO backup;
GRANT SELECT ON TABLE tumour_grading TO readonly;
GRANT SELECT ON TABLE tumour_grading_id_seq TO backup;
GRANT SELECT ON TABLE tumour_grading_id_seq TO readonly;

-- These items are picked out of the SQL dump by searching for 'sample'.
ALTER TABLE ONLY sample ALTER COLUMN id SET DEFAULT nextval('sample_id_seq'::regclass);
ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_name_tissue_id_key UNIQUE (name, tissue_id);
ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_pkey PRIMARY KEY (id);
CREATE INDEX sample_source_id ON sample USING btree (source_id);
CREATE INDEX sample_tissue_id ON sample USING btree (tissue_id);
CREATE INDEX sample_tumour_grading_id ON sample USING btree (tumour_grading_id);

ALTER TABLE ONLY source ALTER COLUMN id SET DEFAULT nextval('source_id_seq'::regclass);
ALTER TABLE ONLY source
    ADD CONSTRAINT source_name_key UNIQUE (name);
ALTER TABLE ONLY source
    ADD CONSTRAINT source_pkey PRIMARY KEY (id);
CREATE INDEX source_father_id ON source USING btree (father_id);
CREATE INDEX source_mother_id ON source USING btree (mother_id);
CREATE INDEX source_name_like ON source USING btree (name varchar_pattern_ops);
CREATE INDEX source_sex_id ON source USING btree (sex_id);
CREATE INDEX source_strain_id ON source USING btree (strain_id);

ALTER TABLE ONLY source_treatment ALTER COLUMN id SET DEFAULT nextval('source_treatment_id_seq'::regclass);
ALTER TABLE ONLY source_treatment
    ADD CONSTRAINT source_treatment_pkey PRIMARY KEY (id);
ALTER TABLE ONLY source_treatment
    ADD CONSTRAINT source_treatment_source_id_date_agent_key UNIQUE (source_id, date, agent_id);
CREATE INDEX source_treatment_agent_id ON source_treatment USING btree (agent_id);
CREATE INDEX source_treatment_dose_unit_id ON source_treatment USING btree (dose_unit_id);
CREATE INDEX source_treatment_source_id ON source_treatment USING btree (source_id);

ALTER TABLE ONLY dose_unit ALTER COLUMN id SET DEFAULT nextval('dose_unit_id_seq'::regclass);
ALTER TABLE ONLY dose_unit
    ADD CONSTRAINT dose_unit_name_key UNIQUE (name);
ALTER TABLE ONLY dose_unit
    ADD CONSTRAINT dose_unit_pkey PRIMARY KEY (id);
CREATE INDEX dose_unit_name_like ON dose_unit USING btree (name varchar_pattern_ops);

ALTER TABLE ONLY treatment_agent ALTER COLUMN id SET DEFAULT nextval('treatment_agent_id_seq'::regclass);
ALTER TABLE ONLY treatment_agent
    ADD CONSTRAINT treatment_agent_name_key UNIQUE (name);
ALTER TABLE ONLY treatment_agent
    ADD CONSTRAINT treatment_agent_pkey PRIMARY KEY (id);
CREATE INDEX treatment_agent_name_like ON treatment_agent USING btree (name varchar_pattern_ops);

ALTER TABLE ONLY tumour_grading ALTER COLUMN id SET DEFAULT nextval('tumour_grading_id_seq'::regclass);
ALTER TABLE ONLY tumour_grading
    ADD CONSTRAINT tumour_grading_name_key UNIQUE (name);
ALTER TABLE ONLY tumour_grading
    ADD CONSTRAINT tumour_grading_pkey PRIMARY KEY (id);
CREATE INDEX tumour_grading_name_like ON tumour_grading USING btree (name varchar_pattern_ops);

ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_source_id_fkey FOREIGN KEY (source_id) REFERENCES source(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_tissue_id_fkey FOREIGN KEY (tissue_id) REFERENCES tissue(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY sample
    ADD CONSTRAINT sample_tumour_grading_id_fkey FOREIGN KEY (tumour_grading_id) REFERENCES tumour_grading(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source
    ADD CONSTRAINT source_sex_id_fkey FOREIGN KEY (sex_id) REFERENCES sex(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source
    ADD CONSTRAINT source_strain_id_fkey FOREIGN KEY (strain_id) REFERENCES strain(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source
    ADD CONSTRAINT father_id_refs_id_2090a647 FOREIGN KEY (father_id) REFERENCES source(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source
    ADD CONSTRAINT mother_id_refs_id_2090a647 FOREIGN KEY (mother_id) REFERENCES source(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source_treatment
    ADD CONSTRAINT source_treatment_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES treatment_agent(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source_treatment
    ADD CONSTRAINT source_treatment_dose_unit_id_fkey FOREIGN KEY (dose_unit_id) REFERENCES dose_unit(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY source_treatment
    ADD CONSTRAINT source_treatment_source_id_fkey FOREIGN KEY (source_id) REFERENCES source(id) DEFERRABLE INITIALLY DEFERRED;

-- End of basic table creation and linking.

-- Create sample IDs from library.individual. These steps will fail if
-- there are remaining inconsistencies in the original library table.
insert into source (name, strain_id, sex_id)
  select distinct individual, strain_id, sex_id from library;
insert into sample (name, tissue_id, source_id)
  select distinct s.name, l.tissue_id, s.id from library l, source s where s.name=l.individual;

-- Link through from library.sample_id to sample.id
alter table library add sample_id integer;
update library lib set sample_id=s.id from sample s where s.name=lib.individual;
CREATE INDEX library_sample_id ON library USING btree (sample_id);
ALTER TABLE ONLY library
    ADD CONSTRAINT library_sample_id_fkey FOREIGN KEY (sample_id) REFERENCES sample(id) DEFERRABLE INITIALLY DEFERRED;

COMMIT;

BEGIN;

-- Make sample.tissue_id required.
alter table sample ALTER column tissue_id SET NOT NULL;

-- Drop individual, tissue, strain, sex from library.
alter table library drop column individual;
alter table library drop column tissue_id;
alter table library drop column strain_id;
alter table library drop column sex_id;

-- Remove other spurious columns from library.
alter table library drop column birthdate;
alter table library drop column harvestdate;
alter table library drop column treatmentdate;
alter table library drop column treatmentagent;
alter table library drop column treatmentdose;

COMMIT;
