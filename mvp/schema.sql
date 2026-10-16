-- 儿童 AI 成长伙伴 MVP 数据库结构（SQLite，字段命名兼容 PostgreSQL 迁移）
-- 依据 V1.1：第二章 2.6 长期记忆层、第四章 4.3、第五章 5.1、第八章

CREATE TABLE IF NOT EXISTS capability_domains (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS learning_goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain_id INTEGER NOT NULL REFERENCES capability_domains(id),
    title TEXT NOT NULL,
    prerequisites TEXT,
    status TEXT NOT NULL DEFAULT 'uncontacted',
    -- 掌握状态（V1.1 4.3）：uncontacted 未接触 / exploring 正在探索 /
    -- learning 正在学习 / partial 初步掌握 / mastered 多次观察后基本掌握 /
    -- recheck 需要重新检查
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    -- 8 种资源类型（V1.1 5.1）：结构化课程 / 视频 / 绘本与文本 / 音频与歌曲 /
    -- 实物玩具与桌游 / 现实生活活动 / 家长或教师提供的学习信息 / AI生成的活动
    topic TEXT,
    domain_ids TEXT,
    goal_ids TEXT,
    age_fit TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending',
    -- pending 待审核 / approved 家长已审核 / rejected 不通过
    contacted INTEGER NOT NULL DEFAULT 0,
    needs_followup INTEGER NOT NULL DEFAULT 0,
    link TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS concept_map (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id INTEGER REFERENCES resources(id),
    topic TEXT NOT NULL,
    concept TEXT NOT NULL,
    goal_id INTEGER REFERENCES learning_goals(id)
    -- V1.1 5.2：资源 → 内容主题 → 学习概念 → 能力目标
);

CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER REFERENCES learning_goals(id),
    observed_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    evidence_kind TEXT NOT NULL,
    -- A 家长确认 / B 互动观察 / C 未验证推测（V1.1 2.6，必须区分）
    performance TEXT NOT NULL,
    help_level TEXT,
    -- 所需帮助：独立 / 少量提示 / 较多帮助 / 全程协助
    independent INTEGER,
    transferred INTEGER,
    note TEXT
);

CREATE TABLE IF NOT EXISTS review_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id INTEGER NOT NULL REFERENCES learning_goals(id),
    next_review_at TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 2,
    done INTEGER NOT NULL DEFAULT 0
);

-- 十个能力领域种子数据（V1.1 第三章）
INSERT OR IGNORE INTO capability_domains (id, name, description) VALUES
(1, '语言与沟通', '母语听说、英语听说、语音意识、绘本阅读、叙述与交流'),
(2, '数学与逻辑', '数字数量对应、数数比较、分类排序规律、形状空间、加减概念'),
(3, '科学与探索', '观察比较、提问预测、尝试验证、因果推理、自然探索'),
(4, '执行功能与自我调节', '工作记忆、抑制冲动、注意力切换、计划、等待轮流'),
(5, '创造力与表达', '绘画音乐手工、故事、角色扮演、搭建、原创想法'),
(6, '社交与情绪能力', '识别表达情绪、理解他人、合作分享、处理分歧、求助'),
(7, '身体与动作发展', '大动作平衡、协调、精细动作、手眼协调、户外运动'),
(8, '生活能力与独立性', '穿衣整理、收纳、生活任务、选择与责任、卫生安全习惯'),
(9, '自主学习与元认知', '选择探索问题、尝试方法、识别何时求助、回顾调整'),
(10, '价值观与AI素养', '诚实责任尊重、规则后果、信息审慎、AI可能出错、向成人确认');
