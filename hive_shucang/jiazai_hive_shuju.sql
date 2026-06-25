-- 智联招聘项目 Hive 关键词装载脚本
-- 当前关键词必须和爬虫、清洗 notebook 顶部配置保持一致。
-- 本脚本直接生成带关键词代码后缀的三张表，不再依赖三张总表。

SET hivevar:guanjianci=数据分析;
SET hivevar:guanjianci_daima=shuju_fenxi;

USE zhaopin_shucang;

SET hive.stats.autogather = false;
SET hive.stats.column.autogather = false;
SET hive.auto.convert.join = false;

DROP TABLE IF EXISTS linshi_yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima};
DROP TABLE IF EXISTS yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima};

CREATE EXTERNAL TABLE linshi_yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima} (
    yuan_shi_gangwei_bianhao             STRING COMMENT 'MySQL原始岗位自增编号',
    yunxing_biaoshi                      STRING COMMENT '来源运行标识',
    guanjianci                           STRING COMMENT '搜索关键词',
    guanjianci_daima                     STRING COMMENT '关键词拼音代码',
    guanjianci_biaoshi                   STRING COMMENT '关键词标识，和 KEYWORD_PATH_CODE 一致',
    chengshi_liebiao                     STRING COMMENT '统一城市名称集合',
    chengshi_daima_liebiao               STRING COMMENT '统一城市代码集合',
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
COMMENT '原始清洗层：当前关键词 CSV 快照'
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
    'separatorChar' = ',',
    'quoteChar' = '"',
    'escapeChar' = '\\'
)
STORED AS TEXTFILE
LOCATION '/user/10967/zhilian_zhaopin/qingxi_jieguo/${hivevar:guanjianci_daima}'
TBLPROPERTIES ('skip.header.line.count' = '1');

CREATE TABLE yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima}
STORED AS ORC
AS
SELECT *
FROM linshi_yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima}
WHERE yuan_shi_gangwei_bianhao RLIKE '^[0-9]+$'
  AND guanjianci IS NOT NULL
  AND TRIM(guanjianci) = '${hivevar:guanjianci}'
  AND guanjianci_daima = '${hivevar:guanjianci_daima}'
  AND guanjianci_biaoshi = '${hivevar:guanjianci_daima}';

DROP TABLE IF EXISTS linshi_yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima};

DROP TABLE IF EXISTS mingxi_gangwei_xinxi_${hivevar:guanjianci_daima};
CREATE TABLE mingxi_gangwei_xinxi_${hivevar:guanjianci_daima}
STORED AS ORC
AS
SELECT
    CAST(yuan_shi_gangwei_bianhao AS BIGINT) AS yuan_shi_gangwei_bianhao,
    yunxing_biaoshi,
    guanjianci,
    guanjianci_daima,
    guanjianci_biaoshi,
    chengshi_liebiao,
    chengshi_daima_liebiao,
    laiyuan_chengshi,
    gangwei_weiyi_biaoshi,
    zhiwei_mingcheng,
    CAST(NULLIF(REGEXP_REPLACE(TRIM(zuidi_xinzi), '万$', ''), '') AS DECIMAL(10,2)) AS zuidi_nianxin_wan,
    CAST(NULLIF(REGEXP_REPLACE(TRIM(zuigao_xinzi), '万$', ''), '') AS DECIMAL(10,2)) AS zuigao_nianxin_wan,
    gongzuo_didian,
    jingyan_yaoqiu,
    xueli_yaoqiu,
    gongzuo_leixing,
    gongzuo_moshi,
    zhiwei_leibie,
    gongsi_mingcheng,
    gongsi_guimo,
    gongsi_xingzhi,
    rongzi_jieduan,
    hangye,
    TO_DATE(fabu_shijian) AS fabu_riqi,
    zhaopin_fuzeren_zhuangtai,
    zhaopin_fuzeren_huoyue_biaoqian,
    jineng_biaoqian,
    zhiwei_miaoshu
FROM (
    SELECT
        yuan_shi_gangwei_bianhao,
        yunxing_biaoshi,
        guanjianci,
        guanjianci_daima,
        guanjianci_biaoshi,
        chengshi_liebiao,
        chengshi_daima_liebiao,
        laiyuan_chengshi,
        gangwei_weiyi_biaoshi,
        zhiwei_mingcheng,
        zuidi_xinzi,
        zuigao_xinzi,
        gongzuo_didian,
        jingyan_yaoqiu,
        xueli_yaoqiu,
        gongzuo_leixing,
        gongzuo_moshi,
        zhiwei_leibie,
        gongsi_mingcheng,
        gongsi_guimo,
        gongsi_xingzhi,
        rongzi_jieduan,
        hangye,
        fabu_shijian,
        zhaopin_fuzeren_zhuangtai,
        zhaopin_fuzeren_huoyue_biaoqian,
        jineng_biaoqian,
        zhiwei_miaoshu,
        ROW_NUMBER() OVER (
            PARTITION BY guanjianci_daima, gangwei_weiyi_biaoshi
            ORDER BY CAST(yuan_shi_gangwei_bianhao AS BIGINT) DESC
        ) AS hanghao
    FROM yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima}
    WHERE yuan_shi_gangwei_bianhao RLIKE '^[0-9]+$'
      AND guanjianci IS NOT NULL
      AND TRIM(guanjianci) = '${hivevar:guanjianci}'
      AND guanjianci_daima = '${hivevar:guanjianci_daima}'
      AND guanjianci_biaoshi = '${hivevar:guanjianci_daima}'
      AND gangwei_weiyi_biaoshi IS NOT NULL
      AND TRIM(gangwei_weiyi_biaoshi) <> ''
) paixu_gangwei
WHERE hanghao = 1;

DROP TABLE IF EXISTS mingxi_gangwei_jineng_${hivevar:guanjianci_daima};
CREATE TABLE mingxi_gangwei_jineng_${hivevar:guanjianci_daima}
STORED AS ORC
AS
SELECT
    yuan_shi_gangwei_bianhao,
    yunxing_biaoshi,
    gangwei_weiyi_biaoshi,
    guanjianci,
    guanjianci_daima,
    guanjianci_biaoshi,
    chengshi_liebiao,
    laiyuan_chengshi,
    zhiwei_mingcheng,
    gongsi_mingcheng,
    jineng_mingcheng,
    jineng_shunxu
FROM (
    SELECT
        gangwei.yuan_shi_gangwei_bianhao,
        gangwei.yunxing_biaoshi,
        gangwei.gangwei_weiyi_biaoshi,
        gangwei.guanjianci,
        gangwei.guanjianci_daima,
        gangwei.guanjianci_biaoshi,
        gangwei.chengshi_liebiao,
        gangwei.laiyuan_chengshi,
        gangwei.zhiwei_mingcheng,
        gangwei.gongsi_mingcheng,
        TRIM(jineng_mingcheng) AS jineng_mingcheng,
        jineng_weizhi + 1 AS jineng_shunxu
    FROM mingxi_gangwei_xinxi_${hivevar:guanjianci_daima} gangwei
    LATERAL VIEW POSEXPLODE(
        SPLIT(COALESCE(gangwei.jineng_biaoqian, ''), '\\s*\\|\\s*')
    ) jineng_shitu AS jineng_weizhi, jineng_mingcheng
    WHERE gangwei.guanjianci_daima = '${hivevar:guanjianci_daima}'
) chaifen_jineng
WHERE jineng_mingcheng <> '';

SELECT 'yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima}' AS biaoming, COUNT(*) AS jilu_shuliang
FROM yuan_shi_gangwei_qingxi_${hivevar:guanjianci_daima}
WHERE yuan_shi_gangwei_bianhao RLIKE '^[0-9]+$'
  AND TRIM(guanjianci) = '${hivevar:guanjianci}'
  AND guanjianci_daima = '${hivevar:guanjianci_daima}'
UNION ALL
SELECT 'mingxi_gangwei_xinxi_${hivevar:guanjianci_daima}', COUNT(*)
FROM mingxi_gangwei_xinxi_${hivevar:guanjianci_daima}
UNION ALL
SELECT 'mingxi_gangwei_jineng_${hivevar:guanjianci_daima}', COUNT(*)
FROM mingxi_gangwei_jineng_${hivevar:guanjianci_daima};
