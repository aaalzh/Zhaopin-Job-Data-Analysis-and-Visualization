-- 智联招聘项目 Hive 单快照装载脚本
-- Spark 已经把每个采集范围的当前 CSV 放入 yuan_shi_gangwei_qingxi 的 LOCATION。

USE zhaopin_shucang;

SET hive.exec.dynamic.partition = true;
SET hive.exec.dynamic.partition.mode = nonstrict;
SET hive.exec.max.dynamic.partitions = 2000;
SET hive.exec.max.dynamic.partitions.pernode = 2000;
SET hive.stats.autogather = false;
SET hive.stats.column.autogather = false;
SET hive.auto.convert.join = false;

-- 同一范围和岗位如果出现重复，保留原始自增编号最大的记录。
WITH paixu_gangwei AS (
    SELECT
        yuan_shi_gangwei_bianhao,
        yunxing_biaoshi,
        guanjianci,
        guanjianci_daima,
        caiji_fanwei_biaoshi,
        chengshi_fanwei,
        chengshi_daima_fanwei,
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
            PARTITION BY caiji_fanwei_biaoshi, gangwei_weiyi_biaoshi
            ORDER BY CAST(yuan_shi_gangwei_bianhao AS BIGINT) DESC
        ) AS hanghao
    FROM yuan_shi_gangwei_qingxi
    WHERE yuan_shi_gangwei_bianhao RLIKE '^[0-9]+$'
      AND guanjianci_daima IS NOT NULL
      AND TRIM(guanjianci_daima) <> ''
      AND caiji_fanwei_biaoshi IS NOT NULL
      AND TRIM(caiji_fanwei_biaoshi) <> ''
      AND gangwei_weiyi_biaoshi IS NOT NULL
      AND TRIM(gangwei_weiyi_biaoshi) <> ''
)
INSERT OVERWRITE TABLE mingxi_gangwei_xinxi
PARTITION (guanjianci_daima, caiji_fanwei_biaoshi)
SELECT
    CAST(yuan_shi_gangwei_bianhao AS BIGINT),
    yunxing_biaoshi,
    guanjianci,
    chengshi_fanwei,
    chengshi_daima_fanwei,
    laiyuan_chengshi,
    gangwei_weiyi_biaoshi,
    zhiwei_mingcheng,
    CAST(NULLIF(REGEXP_REPLACE(TRIM(zuidi_xinzi), '万$', ''), '') AS DECIMAL(10,2)),
    CAST(NULLIF(REGEXP_REPLACE(TRIM(zuigao_xinzi), '万$', ''), '') AS DECIMAL(10,2)),
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
    TO_DATE(fabu_shijian),
    zhaopin_fuzeren_zhuangtai,
    zhaopin_fuzeren_huoyue_biaoqian,
    jineng_biaoqian,
    zhiwei_miaoshu,
    guanjianci_daima,
    caiji_fanwei_biaoshi
FROM paixu_gangwei
WHERE hanghao = 1;

WITH chaifen_jineng AS (
    SELECT
        gangwei.yuan_shi_gangwei_bianhao,
        gangwei.yunxing_biaoshi,
        gangwei.gangwei_weiyi_biaoshi,
        gangwei.guanjianci,
        gangwei.chengshi_fanwei,
        gangwei.laiyuan_chengshi,
        gangwei.zhiwei_mingcheng,
        gangwei.gongsi_mingcheng,
        TRIM(jineng_mingcheng) AS jineng_mingcheng,
        jineng_weizhi + 1 AS jineng_shunxu,
        gangwei.guanjianci_daima,
        gangwei.caiji_fanwei_biaoshi
    FROM mingxi_gangwei_xinxi gangwei
    LATERAL VIEW POSEXPLODE(
        SPLIT(COALESCE(gangwei.jineng_biaoqian, ''), '\\s*\\|\\s*')
    ) jineng_shitu AS jineng_weizhi, jineng_mingcheng
)
INSERT OVERWRITE TABLE mingxi_gangwei_jineng
PARTITION (guanjianci_daima, caiji_fanwei_biaoshi)
SELECT
    yuan_shi_gangwei_bianhao,
    yunxing_biaoshi,
    gangwei_weiyi_biaoshi,
    guanjianci,
    chengshi_fanwei,
    laiyuan_chengshi,
    zhiwei_mingcheng,
    gongsi_mingcheng,
    jineng_mingcheng,
    jineng_shunxu,
    guanjianci_daima,
    caiji_fanwei_biaoshi
FROM chaifen_jineng
WHERE jineng_mingcheng <> '';

SELECT 'yuan_shi_gangwei_qingxi' AS biaoming, COUNT(*) AS jilu_shuliang
FROM yuan_shi_gangwei_qingxi
WHERE yuan_shi_gangwei_bianhao RLIKE '^[0-9]+$'
UNION ALL
SELECT 'mingxi_gangwei_xinxi', COUNT(*) FROM mingxi_gangwei_xinxi
UNION ALL
SELECT 'mingxi_gangwei_jineng', COUNT(*) FROM mingxi_gangwei_jineng;
