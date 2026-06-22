-- 智联招聘项目 Hive 单快照数仓表
-- 表名、字段名、目录名统一使用小写拼音和下划线。
-- 本脚本用于当前不保留旧数据的重建。

CREATE DATABASE IF NOT EXISTS zhaopin_shucang
COMMENT '智联招聘数据仓库'
LOCATION '/user/hive/warehouse/zhaopin_shucang.db';

ALTER DATABASE zhaopin_shucang
SET LOCATION '/user/hive/warehouse/zhaopin_shucang.db';

USE zhaopin_shucang;

DROP TABLE IF EXISTS mingxi_gangwei_jineng;
DROP TABLE IF EXISTS mingxi_gangwei_xinxi;
DROP TABLE IF EXISTS yuan_shi_gangwei_qingxi;

-- 原始清洗层直接读取 Spark 同步到本目录的范围快照 CSV。
-- 每个“关键词＋城市集合”对应一个文件；同范围文件覆盖，不同范围文件共存。
CREATE EXTERNAL TABLE yuan_shi_gangwei_qingxi (
    yuan_shi_gangwei_bianhao             STRING COMMENT 'MySQL原始岗位自增编号',
    yunxing_biaoshi                      STRING COMMENT '来源运行标识',
    guanjianci                           STRING COMMENT '搜索关键词',
    guanjianci_daima                     STRING COMMENT '关键词拼音代码',
    caiji_fanwei_biaoshi                 STRING COMMENT '关键词和城市集合生成的采集范围标识',
    chengshi_fanwei                      STRING COMMENT '规范化城市名称集合',
    chengshi_daima_fanwei                STRING COMMENT '规范化城市代码集合',
    laiyuan_chengshi                     STRING COMMENT '来源城市',
    gangwei_weiyi_biaoshi                STRING COMMENT '岗位稳定唯一标识',
    zhiwei_mingcheng                     STRING COMMENT '职位名称',
    zuidi_xinzi                          STRING COMMENT '最低年薪文本，单位万元',
    zuigao_xinzi                         STRING COMMENT '最高年薪文本，单位万元',
    gongzuo_didian                       STRING COMMENT '工作地点',
    jingyan_yaoqiu                       STRING COMMENT '经验要求',
    xueli_yaoqiu                         STRING COMMENT '学历要求',
    gongzuo_leixing                      STRING COMMENT '工作类型',
    gongzuo_moshi                        STRING COMMENT '工作模式',
    zhiwei_leibie                        STRING COMMENT '职位类别',
    gongsi_mingcheng                     STRING COMMENT '公司名称',
    gongsi_guimo                         STRING COMMENT '公司规模',
    gongsi_xingzhi                       STRING COMMENT '公司性质',
    rongzi_jieduan                       STRING COMMENT '融资阶段',
    hangye                               STRING COMMENT '行业',
    fabu_shijian                         STRING COMMENT '发布时间',
    zhaopin_fuzeren_zhuangtai            STRING COMMENT '招聘负责人状态',
    zhaopin_fuzeren_huoyue_biaoqian      STRING COMMENT '招聘负责人活跃标签',
    jineng_biaoqian                      STRING COMMENT '技能标签汇总',
    zhiwei_miaoshu                       STRING COMMENT '职位描述'
)
COMMENT '原始清洗层：读取各采集范围当前 CSV 快照'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'escapeChar' = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/10967/zhilian_zhaopin/shucang/yuan_shi_gangwei_qingxi'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE EXTERNAL TABLE mingxi_gangwei_xinxi (
    yuan_shi_gangwei_bianhao             BIGINT COMMENT 'MySQL原始岗位自增编号',
    yunxing_biaoshi                      STRING COMMENT '来源运行标识',
    guanjianci                           STRING COMMENT '搜索关键词',
    chengshi_fanwei                      STRING COMMENT '规范化城市名称集合',
    chengshi_daima_fanwei                STRING COMMENT '规范化城市代码集合',
    laiyuan_chengshi                     STRING COMMENT '来源城市',
    gangwei_weiyi_biaoshi                STRING COMMENT '岗位稳定唯一标识',
    zhiwei_mingcheng                     STRING COMMENT '职位名称',
    zuidi_nianxin_wan                    DECIMAL(10,2) COMMENT '最低年薪，单位万元',
    zuigao_nianxin_wan                   DECIMAL(10,2) COMMENT '最高年薪，单位万元',
    gongzuo_didian                       STRING COMMENT '工作地点',
    jingyan_yaoqiu                       STRING COMMENT '经验要求',
    xueli_yaoqiu                         STRING COMMENT '学历要求',
    gongzuo_leixing                      STRING COMMENT '工作类型',
    gongzuo_moshi                        STRING COMMENT '工作模式',
    zhiwei_leibie                        STRING COMMENT '职位类别',
    gongsi_mingcheng                     STRING COMMENT '公司名称',
    gongsi_guimo                         STRING COMMENT '公司规模',
    gongsi_xingzhi                       STRING COMMENT '公司性质',
    rongzi_jieduan                       STRING COMMENT '融资阶段',
    hangye                               STRING COMMENT '行业',
    fabu_riqi                            DATE COMMENT '标准发布日期',
    zhaopin_fuzeren_zhuangtai            STRING COMMENT '招聘负责人状态',
    zhaopin_fuzeren_huoyue_biaoqian      STRING COMMENT '招聘负责人活跃标签',
    jineng_biaoqian                      STRING COMMENT '技能标签汇总',
    zhiwei_miaoshu                       STRING COMMENT '职位描述'
)
COMMENT '岗位明细层：每个采集范围仅保留当前快照'
PARTITIONED BY (
    guanjianci_daima                     STRING COMMENT '关键词拼音代码',
    caiji_fanwei_biaoshi                 STRING COMMENT '采集范围标识'
)
STORED AS ORC
LOCATION '/user/10967/zhilian_zhaopin/shucang/mingxi_gangwei_xinxi'
TBLPROPERTIES ('orc.compress' = 'SNAPPY');

CREATE EXTERNAL TABLE mingxi_gangwei_jineng (
    yuan_shi_gangwei_bianhao             BIGINT COMMENT 'MySQL原始岗位自增编号',
    yunxing_biaoshi                      STRING COMMENT '来源运行标识',
    gangwei_weiyi_biaoshi                STRING COMMENT '岗位稳定唯一标识',
    guanjianci                           STRING COMMENT '搜索关键词',
    chengshi_fanwei                      STRING COMMENT '规范化城市名称集合',
    laiyuan_chengshi                     STRING COMMENT '来源城市',
    zhiwei_mingcheng                     STRING COMMENT '职位名称',
    gongsi_mingcheng                     STRING COMMENT '公司名称',
    jineng_mingcheng                     STRING COMMENT '拆分后的技能名称',
    jineng_shunxu                        INT COMMENT '技能在原字段中的顺序，从1开始'
)
COMMENT '岗位技能明细层'
PARTITIONED BY (
    guanjianci_daima                     STRING COMMENT '关键词拼音代码',
    caiji_fanwei_biaoshi                 STRING COMMENT '采集范围标识'
)
STORED AS ORC
LOCATION '/user/10967/zhilian_zhaopin/shucang/mingxi_gangwei_jineng'
TBLPROPERTIES ('orc.compress' = 'SNAPPY');

SHOW TABLES;
