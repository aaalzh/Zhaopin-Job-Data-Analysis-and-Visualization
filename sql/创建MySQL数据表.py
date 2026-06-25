"""创建或重建智联招聘项目 MySQL 数据表。

默认只创建不存在的表：
    python sql/创建MySQL数据表.py

明确允许丢弃现有数据时重建全部表：
    python sql/创建MySQL数据表.py --chongjian
"""

import argparse
import pymysql


from db_config import MYSQL_DATABASE, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_PORT, MYSQL_USER


XIN_BIAO = [
    "yuan_shi_gangwei_xinxi",
    "yuan_shi_gongsi_xinxi",
    "yuan_shi_zhaopin_fuzeren_xinxi",
    "pachong_yunxing_rizhi",
    "qingxi_gangwei_mingxi",
    "qingxi_gongsi_xinxi",
    "qingxi_zhaopin_fuzeren_xinxi",
    "qingxi_yunxing_rizhi",
]

TONGJI_JIEGUO_BIAO = "tongji_fenxi_jieguo"
SUOYOU_BIAO = XIN_BIAO + [TONGJI_JIEGUO_BIAO]


CREATE_TABLE_SQL_LIST = [
    """
    CREATE TABLE IF NOT EXISTS `yuan_shi_gangwei_xinxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '本次运行唯一标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词代码生成的关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '本行来源城市',
      `chengshi_daima` varchar(50) DEFAULT NULL COMMENT '本行城市代码',
      `yema` int DEFAULT NULL COMMENT '来源页码',
      `gangwei_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '岗位稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `zhiwei_bianhao` varchar(100) DEFAULT NULL COMMENT '职位编号标识',
      `zhiwei_xuhao` varchar(100) DEFAULT NULL COMMENT '职位展示编号',
      `zhiwei_mingcheng` varchar(300) DEFAULT NULL COMMENT '职位名称',
      `zhiwei_lianjie` varchar(1000) DEFAULT NULL COMMENT '职位链接',
      `xinzi` varchar(100) DEFAULT NULL COMMENT '薪资',
      `xinzi_yuanshi_qujian` varchar(100) DEFAULT NULL COMMENT '薪资原始区间',
      `xinzi_leixing` varchar(100) DEFAULT NULL COMMENT '薪资类型',
      `xinzi_fafang_cishu` varchar(100) DEFAULT NULL COMMENT '薪资发放次数',
      `gongzuo_chengshi` varchar(100) DEFAULT NULL COMMENT '工作城市',
      `xingzhengqu` varchar(100) DEFAULT NULL COMMENT '行政区',
      `shangquan_jiedao` varchar(200) DEFAULT NULL COMMENT '商圈或街道',
      `gongzuo_didian` varchar(300) DEFAULT NULL COMMENT '工作地点展示',
      `xiangxi_dizhi` varchar(500) DEFAULT NULL COMMENT '详细地址',
      `jingdu` varchar(80) DEFAULT NULL COMMENT '经度',
      `weidu` varchar(80) DEFAULT NULL COMMENT '纬度',
      `jingyan_yaoqiu` varchar(100) DEFAULT NULL COMMENT '经验要求',
      `xueli_yaoqiu` varchar(100) DEFAULT NULL COMMENT '学历要求',
      `gongzuo_leixing` varchar(100) DEFAULT NULL COMMENT '工作类型',
      `gongzuo_moshi` varchar(100) DEFAULT NULL COMMENT '工作模式',
      `zhiwei_leibie` varchar(200) DEFAULT NULL COMMENT '职位类别',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `fabu_shijian` varchar(100) DEFAULT NULL COMMENT '发布时间',
      `shouci_fabu_shijian` varchar(100) DEFAULT NULL COMMENT '首次发布时间',
      `fabu_riqi_wenben` varchar(100) DEFAULT NULL COMMENT '发布日期文本',
      `shifou_xin_zhiwei` varchar(50) DEFAULT NULL COMMENT '是否新职位',
      `zhaopin_renshu` varchar(50) DEFAULT NULL COMMENT '招聘人数',
      `zhiwei_biaoqian_huizong` text COMMENT '职位标签汇总',
      `sousuo_mingzhong_guanjianci` text COMMENT '搜索命中关键词',
      `jineng_biaoqian` text COMMENT '技能标签',
      `fuli_biaoqian` text COMMENT '福利标签',
      `fuli_mingxi` text COMMENT '福利明细',
      `gongzuo_shijian` text COMMENT '工作时间',
      `baogao_baozhang_xiang` text COMMENT '报告项或保障项',
      `zhiwei_miaoshu` longtext COMMENT '职位描述',
      `zhiwei_liangdian` longtext COMMENT '职位亮点',
      `zhiwei_zhaiyao` longtext COMMENT '职位摘要',
      `renzheng_shouhu_xinxi` text COMMENT '认证或守护信息',
      `yuanshi_neirong` longtext COMMENT '原始接口内容',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_yuanshi_gangwei_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_yuanshi_gangwei_yunxing` (`yunxing_biaoshi`),
      KEY `suoyin_yuanshi_gangwei_biaoshi` (`gangwei_weiyi_biaoshi`),
      KEY `suoyin_yuanshi_gangwei_chengshi` (`laiyuan_chengshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始岗位信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `yuan_shi_gongsi_xinxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '本次运行唯一标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '本行来源城市',
      `gongsi_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '公司稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `gongsi_bianhao` varchar(100) DEFAULT NULL COMMENT '公司编号',
      `gongsi_lianjie` varchar(1000) DEFAULT NULL COMMENT '公司链接',
      `gongsi_tubiao_lianjie` varchar(1000) DEFAULT NULL COMMENT '公司图标链接',
      `gongsi_guimo` varchar(100) DEFAULT NULL COMMENT '公司规模',
      `gongsi_xingzhi` varchar(100) DEFAULT NULL COMMENT '公司性质',
      `rongzi_jieduan` varchar(100) DEFAULT NULL COMMENT '融资阶段',
      `hangye` varchar(200) DEFAULT NULL COMMENT '行业',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_yuanshi_gongsi_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_yuanshi_gongsi_yunxing` (`yunxing_biaoshi`),
      KEY `suoyin_yuanshi_gongsi_biaoshi` (`gongsi_weiyi_biaoshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始公司信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `yuan_shi_zhaopin_fuzeren_xinxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '本次运行唯一标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '本行来源城市',
      `gangwei_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '岗位稳定唯一标识',
      `zhaopin_fuzeren_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '招聘负责人稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `zhiwei_mingcheng` varchar(300) DEFAULT NULL COMMENT '职位名称',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `zhaopin_fuzeren_xingming` varchar(100) DEFAULT NULL COMMENT '招聘负责人姓名',
      `zhaopin_fuzeren_zhiwei` varchar(200) DEFAULT NULL COMMENT '招聘负责人职位',
      `zhaopin_fuzeren_zhuangtai` varchar(200) DEFAULT NULL COMMENT '招聘负责人状态',
      `zhaopin_fuzeren_huoyue_biaoqian` varchar(500) DEFAULT NULL COMMENT '招聘负责人活跃标签',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_yuanshi_fuzeren_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_yuanshi_fuzeren_yunxing` (`yunxing_biaoshi`),
      KEY `suoyin_yuanshi_fuzeren_gangwei` (`gangwei_weiyi_biaoshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='原始招聘负责人信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `pachong_yunxing_rizhi` (
      `rizhi_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '日志编号',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '最近一次运行标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `jihua_chengshi_shuliang` int DEFAULT 0 COMMENT '计划城市数量',
      `chenggong_chengshi_shuliang` int DEFAULT 0 COMMENT '成功城市数量',
      `shibai_chengshi_shuliang` int DEFAULT 0 COMMENT '失败城市数量',
      `gangwei_jilu_shuliang` int DEFAULT 0 COMMENT '岗位记录数量',
      `gongsi_jilu_shuliang` int DEFAULT 0 COMMENT '公司记录数量',
      `zhaopin_fuzeren_jilu_shuliang` int DEFAULT 0 COMMENT '招聘负责人记录数量',
      `yunxing_zhuangtai` varchar(50) DEFAULT NULL COMMENT '运行状态',
      `yunxing_shuoming` varchar(1000) DEFAULT NULL COMMENT '运行说明',
      `kaishi_shijian` datetime DEFAULT NULL COMMENT '开始时间',
      `jieshu_shijian` datetime DEFAULT NULL COMMENT '结束时间',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
      `gengxin_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
      PRIMARY KEY (`rizhi_bianhao`),
      UNIQUE KEY `weiyi_pachong_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_pachong_guanjianci` (`guanjianci`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每个关键词一条最新爬虫日志'
    """,
    """
    CREATE TABLE IF NOT EXISTS `qingxi_gangwei_mingxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yuan_shi_gangwei_bianhao` bigint DEFAULT NULL COMMENT '原始岗位自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '来源运行标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '来源城市',
      `gangwei_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '岗位稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `zhiwei_mingcheng` varchar(300) DEFAULT NULL COMMENT '职位名称',
      `zuidi_xinzi` varchar(50) DEFAULT NULL COMMENT '最低年薪文本',
      `zuigao_xinzi` varchar(50) DEFAULT NULL COMMENT '最高年薪文本',
      `gongzuo_didian` varchar(300) DEFAULT NULL COMMENT '工作地点',
      `jingyan_yaoqiu` varchar(100) DEFAULT NULL COMMENT '经验要求',
      `xueli_yaoqiu` varchar(100) DEFAULT NULL COMMENT '学历要求',
      `gongzuo_leixing` varchar(100) DEFAULT NULL COMMENT '工作类型',
      `gongzuo_moshi` varchar(100) DEFAULT NULL COMMENT '工作模式',
      `zhiwei_leibie` varchar(200) DEFAULT NULL COMMENT '职位类别',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `gongsi_guimo` varchar(100) DEFAULT NULL COMMENT '公司规模',
      `gongsi_xingzhi` varchar(100) DEFAULT NULL COMMENT '公司性质',
      `rongzi_jieduan` varchar(100) DEFAULT NULL COMMENT '融资阶段',
      `hangye` varchar(200) DEFAULT NULL COMMENT '行业',
      `fabu_shijian` varchar(100) DEFAULT NULL COMMENT '发布时间',
      `zhaopin_fuzeren_zhuangtai` varchar(200) DEFAULT NULL COMMENT '招聘负责人状态',
      `zhaopin_fuzeren_huoyue_biaoqian` varchar(500) DEFAULT NULL COMMENT '招聘负责人活跃标签',
      `jineng_biaoqian` text COMMENT '技能标签',
      `zhiwei_miaoshu` longtext COMMENT '职位描述',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_qingxi_gangwei_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_qingxi_gangwei_yunxing` (`yunxing_biaoshi`),
      KEY `suoyin_qingxi_gangwei_biaoshi` (`gangwei_weiyi_biaoshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗岗位明细表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `qingxi_gongsi_xinxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '来源运行标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '来源城市',
      `gongsi_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '公司稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `gongsi_guimo` varchar(100) DEFAULT NULL COMMENT '公司规模',
      `gongsi_xingzhi` varchar(100) DEFAULT NULL COMMENT '公司性质',
      `rongzi_jieduan` varchar(100) DEFAULT NULL COMMENT '融资阶段',
      `hangye` varchar(200) DEFAULT NULL COMMENT '行业',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_qingxi_gongsi_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_qingxi_gongsi_biaoshi` (`gongsi_weiyi_biaoshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗公司信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `qingxi_zhaopin_fuzeren_xinxi` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '来源运行标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `laiyuan_chengshi` varchar(100) DEFAULT NULL COMMENT '来源城市',
      `gangwei_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '岗位稳定唯一标识',
      `zhaopin_fuzeren_weiyi_biaoshi` char(32) DEFAULT NULL COMMENT '招聘负责人稳定唯一标识',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '写入时间',
      `zhiwei_mingcheng` varchar(300) DEFAULT NULL COMMENT '职位名称',
      `gongsi_mingcheng` varchar(300) DEFAULT NULL COMMENT '公司名称',
      `zhaopin_fuzeren_zhuangtai` varchar(200) DEFAULT NULL COMMENT '招聘负责人状态',
      `zhaopin_fuzeren_huoyue_biaoqian` varchar(500) DEFAULT NULL COMMENT '招聘负责人活跃标签',
      PRIMARY KEY (`zizeng_bianhao`),
      KEY `suoyin_qingxi_fuzeren_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_qingxi_fuzeren_gangwei` (`gangwei_weiyi_biaoshi`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='清洗招聘负责人信息表'
    """,
    """
    CREATE TABLE IF NOT EXISTS `qingxi_yunxing_rizhi` (
      `rizhi_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '日志编号',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `yunxing_biaoshi` varchar(150) NOT NULL COMMENT '来源运行标识',
      `guanjianci` varchar(100) NOT NULL COMMENT '搜索关键词',
      `guanjianci_daima` varchar(100) NOT NULL COMMENT '关键词拼音代码',
      `chengshi_liebiao` text COMMENT '规范化城市名称集合',
      `chengshi_daima_liebiao` text COMMENT '规范化城市代码集合',
      `gangwei_jilu_shuliang` int DEFAULT 0 COMMENT '岗位记录数量',
      `gongsi_jilu_shuliang` int DEFAULT 0 COMMENT '公司记录数量',
      `zhaopin_fuzeren_jilu_shuliang` int DEFAULT 0 COMMENT '招聘负责人记录数量',
      `shuchu_lujing` varchar(1000) DEFAULT NULL COMMENT '分布式文件系统输出路径',
      `yunxing_zhuangtai` varchar(50) DEFAULT NULL COMMENT '运行状态',
      `yunxing_shuoming` varchar(1000) DEFAULT NULL COMMENT '运行说明',
      `kaishi_shijian` datetime DEFAULT NULL COMMENT '开始时间',
      `jieshu_shijian` datetime DEFAULT NULL COMMENT '结束时间',
      `chuangjian_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '首次创建时间',
      `gengxin_shijian` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最近更新时间',
      PRIMARY KEY (`rizhi_bianhao`),
      UNIQUE KEY `weiyi_qingxi_guanjianci_biaoshi` (`guanjianci_biaoshi`),
      KEY `suoyin_qingxi_guanjianci` (`guanjianci`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每个关键词一条最新清洗日志'
    """,
    """
    CREATE TABLE IF NOT EXISTS `tongji_fenxi_jieguo` (
      `zizeng_bianhao` bigint NOT NULL AUTO_INCREMENT COMMENT '自增编号',
      `guanjianci_biaoshi` varchar(100) NOT NULL COMMENT '关键词标识',
      `guanjianci` varchar(100) DEFAULT NULL COMMENT '搜索关键词',
      `tongji_leixing` varchar(100) NOT NULL COMMENT '统计类型',
      `jieguo_json` longtext NOT NULL COMMENT '统计结果JSON',
      `gengxin_shijian` datetime NOT NULL COMMENT '更新时间',
      PRIMARY KEY (`zizeng_bianhao`),
      UNIQUE KEY `weiyi_guanjianci_tongji` (`guanjianci_biaoshi`, `tongji_leixing`),
      KEY `suoyin_tongji_leixing` (`tongji_leixing`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Spark统计分析结果'
    """,
]


def get_mysql_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=int(MYSQL_PORT),
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=True,
    )


def create_tables(chongjian=False):
    with get_mysql_connection() as connection:
        with connection.cursor() as cursor:
            if chongjian:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                for table in SUOYOU_BIAO:
                    cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                print("当前业务表和统计结果表已删除，正在重建。")

            for sql in CREATE_TABLE_SQL_LIST:
                cursor.execute(sql)

    print("MySQL 业务表和统计结果表结构已准备好：")
    for table in SUOYOU_BIAO:
        print(f"- {table}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chongjian", action="store_true", help="删除旧表和当前表后重建，现有数据会丢失")
    args = parser.parse_args()
    create_tables(chongjian=args.chongjian)
