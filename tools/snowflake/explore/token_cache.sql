use role rl_ssdb_Integration_Lr_Strategy_Rw;
use database ssdb_Integration;
use schema lr_strategy;
--Why every run opens the browser login: the connector caches the SSO token (client_store_temporary_credential, in
--connections.toml) only when the account parameter ALLOW_ID_TOKEN is true, which only an account administrator can set
--(docs.snowflake.com admin-security-fed-auth-use: "alter account set allow_id_token = true").  Read only, one result:
--the parameter's value (false: ask the Snowflake administrators to enable connection caching).  Not tested: a SHOW.
SHOW PARAMETERS LIKE 'ALLOW_ID_TOKEN' IN ACCOUNT;
