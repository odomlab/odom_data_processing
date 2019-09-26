begin;
create table lane_external_record (
    id integer NOT NULL,
    lane_id integer NOT NULL,
    externalrecord_id integer NOT NULL
);
ALTER TABLE public.lane_external_record OWNER TO chipseq;
CREATE SEQUENCE lane_externalrecord_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER TABLE public.lane_externalrecord_id_seq OWNER TO chipseq;
ALTER SEQUENCE lane_externalrecord_id_seq OWNED BY lane_external_record.id;
ALTER TABLE ONLY lane_external_record ALTER COLUMN id SET DEFAULT nextval('lane_externalrecord_id_seq'::regclass);
ALTER TABLE ONLY lane_external_record
    ADD CONSTRAINT lane_external_record_lane_id_key UNIQUE (lane_id, externalrecord_id);
ALTER TABLE ONLY lane_external_record
    ADD CONSTRAINT lane_external_record_pkey PRIMARY KEY (id);
CREATE INDEX lane_external_record_lane_id ON lane_external_record USING btree (lane_id);
CREATE INDEX lane_external_record_externalrecord_id ON lane_external_record USING btree (externalrecord_id);
ALTER TABLE ONLY lane_external_record
    ADD CONSTRAINT lane_id_refs_id_1ec5ec0d FOREIGN KEY (lane_id) REFERENCES lane(id) DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE ONLY lane_external_record
    ADD CONSTRAINT lane_external_record_externalrecord_id_fkey FOREIGN KEY (externalrecord_id) REFERENCES external_record(id) DEFERRABLE INITIALLY DEFERRED;
commit;
