-- NOTE that this file should only be run *after* the django
-- repository application is fully set up; that includes running the
-- SQL statements in repository/additional.sql to set up
-- non-django-managed tables.

-- Various statements which are designed to be run after the models
-- have been loaded with syncdb and we've inserted the legacy data
-- into those tables.

-- IMPLEMENTATION NOTE: it would be good if everything in this file
-- can be run multiple times without either complaining or creating
-- unexpected changes in the database. It is anticipated that this
-- will need to be run every time a schema change is made during the
-- interim period where we're supporting both ORMs (django and cs_db.py).

-- First, add database defaults where necessary. This is to support
-- the old cs_db code and provide a measure of defensive coding where
-- django only maintains such things at the application level.
begin;
alter table alignment alter column headtrim        set default 0;
alter table alignment alter column tailtrim        set default 0;
alter table antibody alter column lot_number      set default 'unknown';
alter table filetype  alter column gzip            set default true;
alter table lane      alter column paired          set default false;
alter table lane      alter column failed          set default false;
alter table lanefile alter column pipeline        set default 'chipseq'; -- FIXME
alter table library   alter column bad             set default false;
alter table library   alter column paired          set default false;
alter table project   alter column shortnames      set default true;
alter table project   alter column filtered        set default true;
alter table status   alter column colour          set default '#FFFFFF';
alter table status    alter column lanerelevant    set default false;
alter table status    alter column libraryrelevant set default false;
alter table status    alter column sortcode        set default 0;
commit;

-- Second, update all sequences so we don't find ourselves running
-- into old IDs. This is made slightly more complex by the possible
-- presence of empty tables.
begin;
select setval('adapter_id_seq'::regclass, coalesce((select max(id) from adapter), 1), true);
select setval('alnfile_id_seq'::regclass, coalesce((select max(id) from alnfile), 1), true);
select setval('antibody_id_seq'::regclass, coalesce((select max(id) from antibody), 1), true);
select setval('auth_group_id_seq'::regclass, coalesce((select max(id) from auth_group), 1), true);
select setval('auth_group_permissions_id_seq'::regclass, coalesce((select max(id) from auth_group_permissions), 1), true);
select setval('auth_permission_id_seq'::regclass, coalesce((select max(id) from auth_permission), 1), true);
select setval('auth_user_id_seq'::regclass, coalesce((select max(id) from auth_user), 1), true);
select setval('auth_user_groups_id_seq'::regclass, coalesce((select max(id) from auth_user_groups), 1), true);
select setval('auth_user_user_permissions_id_seq'::regclass, coalesce((select max(id) from auth_user_user_permissions), 1), true);
select setval('data_process_id_seq'::regclass, coalesce((select max(id) from data_process), 1), true);
select setval('data_provenance_id_seq'::regclass, coalesce((select max(id) from data_provenance), 1), true);
select setval('django_admin_log_id_seq'::regclass, coalesce((select max(id) from django_admin_log), 1), true);
select setval('django_content_type_id_seq'::regclass, coalesce((select max(id) from django_content_type), 1), true);
select setval('django_site_id_seq'::regclass, coalesce((select max(id) from django_site), 1), true);
select setval('facility_id_seq'::regclass, coalesce((select max(id) from facility), 1), true);
select setval('factor_id_seq'::regclass, coalesce((select max(id) from factor), 1), true);
select setval('filetype_id_seq'::regclass, coalesce((select max(id) from filetype), 1), true);
select setval('genome_id_seq'::regclass, coalesce((select max(id) from genome), 1), true);
select setval('lane_id_seq'::regclass, coalesce((select max(id) from lane), 1), true);
select setval('lanefile_id_seq'::regclass, coalesce((select max(id) from lanefile), 1), true);
select setval('libfile_id_seq'::regclass, coalesce((select max(id) from libfile), 1), true);
select setval('library_id_seq'::regclass, coalesce((select max(id) from library), 1), true);
select setval('library_project_id_seq'::regclass, coalesce((select max(id) from library_project), 1), true);
select setval('library_name_map_id_seq'::regclass, coalesce((select max(id) from library_name_map), 1), true);
select setval('libtype_id_seq'::regclass, coalesce((select max(id) from libtype), 1), true);
select setval('linkerset_id_seq'::regclass, coalesce((select max(id) from linkerset), 1), true);
select setval('peakfile_id_seq'::regclass, coalesce((select max(id) from peakfile), 1), true);
select setval('program_id_seq'::regclass, coalesce((select max(id) from program), 1), true);
select setval('project_id_seq'::regclass, coalesce((select max(id) from project), 1), true);
select setval('project_users_id_seq'::regclass, coalesce((select max(id) from project_users), 1), true);
select setval('qcfile_id_seq'::regclass, coalesce((select max(id) from qcfile), 1), true);
select setval('sex_id_seq'::regclass, coalesce((select max(id) from sex), 1), true);
select setval('sitetree_tree_id_seq'::regclass, coalesce((select max(id) from sitetree_tree), 1), true);
select setval('sitetree_treeitem_id_seq'::regclass, coalesce((select max(id) from sitetree_treeitem), 1), true);
select setval('sitetree_treeitem_access_permissions_id_seq'::regclass, coalesce((select max(id) from sitetree_treeitem_access_permissions), 1), true);
select setval('status_id_seq'::regclass, coalesce((select max(id) from status), 1), true);
select setval('strain_id_seq'::regclass, coalesce((select max(id) from strain), 1), true);
select setval('tissue_id_seq'::regclass, coalesce((select max(id) from tissue), 1), true);
select setval('library_name_ignore_id_seq'::regclass, coalesce((select max(id) from library_name_ignore), 1), true);
commit;

-- Third, add read-only access for each table to the backup and
-- readonly users.
begin;
grant select on table adapter to backup;
grant select on table adapter to readonly;
grant select on table alignment to backup;
grant select on table alignment to readonly;
grant select on table alnfile to backup;
grant select on table alnfile to readonly;
grant select on table antibody to backup;
grant select on table antibody to readonly;
grant select on table auth_group to backup;
grant select on table auth_group to readonly;
grant select on table auth_group_permissions to backup;
grant select on table auth_group_permissions to readonly;
grant select on table auth_permission to backup;
grant select on table auth_permission to readonly;
grant select on table auth_user to backup;
grant select on table auth_user to readonly;
grant select on table auth_user_groups to backup;
grant select on table auth_user_groups to readonly;
grant select on table auth_user_user_permissions to backup;
grant select on table auth_user_user_permissions to readonly;
grant select on table data_process to backup;
grant select on table data_process to readonly;
grant select on table data_provenance to backup;
grant select on table data_provenance to readonly;
grant select on table django_admin_log to backup;
grant select on table django_admin_log to readonly;
grant select on table django_content_type to backup;
grant select on table django_content_type to readonly;
grant select on table django_session to backup;
grant select on table django_session to readonly;
grant select on table django_site to backup;
grant select on table django_site to readonly;
grant select on table facility to backup;
grant select on table facility to readonly;
grant select on table factor to backup;
grant select on table factor to readonly;
grant select on table filetype to backup;
grant select on table filetype to readonly;
grant select on table genome to backup;
grant select on table genome to readonly;
grant select on table lane to backup;
grant select on table lane to readonly;
grant select on table lane_qc to backup;
grant select on table lane_qc to readonly;
grant select on table lanefile to backup;
grant select on table lanefile to readonly;
grant select on table libfile to backup;
grant select on table libfile to readonly;
grant select on table library to backup;
grant select on table library to readonly;
grant select on table library_name_ignore to backup;
grant select on table library_name_ignore to readonly;
grant select on table library_name_map to backup;
grant select on table library_name_map to readonly;
grant select on table library_project to backup;
grant select on table library_project to readonly;
grant select on table libtype to backup;
grant select on table libtype to readonly;
grant select on table linkerset to backup;
grant select on table linkerset to readonly;
grant select on table peakcalls to backup;
grant select on table peakcalls to readonly;
grant select on table peakfile to backup;
grant select on table peakfile to readonly;
grant select on table program to backup;
grant select on table program to readonly;
grant select on table project to backup;
grant select on table project to readonly;
grant select on table project_users to backup;
grant select on table project_users to readonly;
grant select on table qcfile to backup;
grant select on table qcfile to readonly;
grant select on table qc_value to backup;
grant select on table qc_value to readonly;
grant select on table sex to backup;
grant select on table sex to readonly;
grant select on table sitetree_tree to backup;
grant select on table sitetree_tree to readonly;
grant select on table sitetree_treeitem to backup;
grant select on table sitetree_treeitem to readonly;
grant select on table sitetree_treeitem_access_permissions to backup;
grant select on table sitetree_treeitem_access_permissions to readonly;
grant select on table status to backup;
grant select on table status to readonly;
grant select on table strain to backup;
grant select on table strain to readonly;
grant select on table tissue to backup;
grant select on table tissue to readonly;
grant select on table external_record to backup;
grant select on table external_record to readonly;
grant select on table external_repository to backup;
grant select on table external_repository to readonly;
grant select on table lane_external_record to backup;
grant select on table lane_external_record to readonly;
commit;

begin;
grant select on table adapter_id_seq to backup;
grant select on table adapter_id_seq to readonly;
grant select on table alnfile_id_seq to backup;
grant select on table alnfile_id_seq to readonly;
grant select on table antibody_id_seq to backup;
grant select on table antibody_id_seq to readonly;
grant select on table auth_group_id_seq to backup;
grant select on table auth_group_id_seq to readonly;
grant select on table auth_group_permissions_id_seq to backup;
grant select on table auth_group_permissions_id_seq to readonly;
grant select on table auth_permission_id_seq to backup;
grant select on table auth_permission_id_seq to readonly;
grant select on table auth_user_id_seq to backup;
grant select on table auth_user_id_seq to readonly;
grant select on table auth_user_groups_id_seq to backup;
grant select on table auth_user_groups_id_seq to readonly;
grant select on table auth_user_user_permissions_id_seq to backup;
grant select on table auth_user_user_permissions_id_seq to readonly;
grant select on table data_process_id_seq to backup;
grant select on table data_process_id_seq to readonly;
grant select on table data_provenance_id_seq to backup;
grant select on table data_provenance_id_seq to readonly;
grant select on table django_admin_log_id_seq to backup;
grant select on table django_admin_log_id_seq to readonly;
grant select on table django_content_type_id_seq to backup;
grant select on table django_content_type_id_seq to readonly;
grant select on table django_site_id_seq to backup;
grant select on table django_site_id_seq to readonly;
grant select on table facility_id_seq to backup;
grant select on table facility_id_seq to readonly;
grant select on table factor_id_seq to backup;
grant select on table factor_id_seq to readonly;
grant select on table filetype_id_seq to backup;
grant select on table filetype_id_seq to readonly;
grant select on table genome_id_seq to backup;
grant select on table genome_id_seq to readonly;
grant select on table lane_id_seq to backup;
grant select on table lane_id_seq to readonly;
grant select on table lanefile_id_seq to backup;
grant select on table lanefile_id_seq to readonly;
grant select on table libfile_id_seq to backup;
grant select on table libfile_id_seq to readonly;
grant select on table library_id_seq to backup;
grant select on table library_id_seq to readonly;
grant select on table library_name_ignore_id_seq to backup;
grant select on table library_name_ignore_id_seq to readonly;
grant select on table library_name_map_id_seq to backup;
grant select on table library_name_map_id_seq to readonly;
grant select on table library_project_id_seq to backup;
grant select on table library_project_id_seq to readonly;
grant select on table libtype_id_seq to backup;
grant select on table libtype_id_seq to readonly;
grant select on table linkerset_id_seq to backup;
grant select on table linkerset_id_seq to readonly;
grant select on table peakfile_id_seq to backup;
grant select on table peakfile_id_seq to readonly;
grant select on table program_id_seq to backup;
grant select on table program_id_seq to readonly;
grant select on table project_id_seq to backup;
grant select on table project_id_seq to readonly;
grant select on table project_users_id_seq to backup;
grant select on table project_users_id_seq to readonly;
grant select on table qcfile_id_seq to backup;
grant select on table qcfile_id_seq to readonly;
grant select on table qc_value_id_seq to backup;
grant select on table qc_value_id_seq to readonly;
grant select on table sex_id_seq to backup;
grant select on table sex_id_seq to readonly;
grant select on table sitetree_tree_id_seq to backup;
grant select on table sitetree_tree_id_seq to readonly;
grant select on table sitetree_treeitem_id_seq to backup;
grant select on table sitetree_treeitem_id_seq to readonly;
grant select on table sitetree_treeitem_access_permissions_id_seq to backup;
grant select on table sitetree_treeitem_access_permissions_id_seq to readonly;
grant select on table status_id_seq to backup;
grant select on table status_id_seq to readonly;
grant select on table strain_id_seq to backup;
grant select on table strain_id_seq to readonly;
grant select on table tissue_id_seq to backup;
grant select on table tissue_id_seq to readonly;
grant select on table external_record_id_seq to backup;
grant select on table external_record_id_seq to readonly;
grant select on table external_repository_id_seq to backup;
grant select on table external_repository_id_seq to readonly;
grant select on table lane_externalrecord_id_seq to backup;
grant select on table lane_externalrecord_id_seq to readonly;
commit;

alter table public.library_extra OWNER TO chipseq;
grant select on table library_extra to chipseq; -- or whatever is in SETTINGS.py
grant select on table library_extra to backup;
grant select on table library_extra to readonly;
commit;

