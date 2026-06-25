-- 智联招聘项目 Hive 数仓初始化脚本
-- 这里只初始化数据库，不删除任何已有表。
-- 关键词后缀表由 jiazai_hive_shuju.sql 按当前关键词直接生成。

CREATE DATABASE IF NOT EXISTS zhaopin_shucang
COMMENT '智联招聘数据仓库'
LOCATION '/user/hive/warehouse/zhaopin_shucang.db';

ALTER DATABASE zhaopin_shucang
SET LOCATION '/user/hive/warehouse/zhaopin_shucang.db';

USE zhaopin_shucang;

SHOW TABLES;
