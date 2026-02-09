/**
 * MOCKデータ
 * 開発・テスト用のダミーデータ。将来的にはDB/APIに置き換え。
 */
import { searchEntities } from "./entity-search";
import type { EntityType, StringEntity } from "./types";

// 基準日時（一貫性のため固定）
const BASE_DATE = new Date("2026-01-24T00:00:00Z");

// ===== Material タイプのデータ =====
const MATERIAL_NAMES = [
  "A5052",
  "A6061-T6",
  "SUS304",
  "SUS316L",
  "Ti-6Al-4V",
  "Inconel 718",
  "Cu-ETP",
  "PEEK",
];

const MATERIAL_VARIANTS: {
  label: string;
  tags: string[];
  props: Record<string, string>;
  body: string;
}[] = [
  {
    label: "熱物性",
    tags: ["conductivity", "thermal"],
    props: { conductivity: "236" },
    body: `*conductivity, type=iso\n 236.`,
  },
  {
    label: "弾塑性",
    tags: ["elastic", "plastic", "structural"],
    props: { elastic: "100.e3", plastic: "100/150/200" },
    body: `*elastic\n 100.e3, 0.33\n*plastic\n 100., 0.`,
  },
];

const MATERIALS: StringEntity[] = MATERIAL_NAMES.map((name, i) => {
  const variant = MATERIAL_VARIANTS[i % MATERIAL_VARIANTS.length];
  return {
    id: `mat-${i + 1}`,
    name: `${name}`,
    body: `*Material, name=${name}\n${variant.body}`,
    entityType: "Material" as EntityType,
    sysTags: ["material", "abaqus"],
    userTags: variant.tags,
    sysProps: { extension: "inp" },
    userProps: variant.props,
    remark: variant.label,
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - i * 86400000).toISOString(),
  };
});

// ===== Tag タイプのデータ =====
const TAG_DEFINITIONS = [
  {
    name: "thermal",
    desc: "熱解析関連のタグ",
    related: ["conductivity", "expansion"],
  },
  {
    name: "structural",
    desc: "構造解析関連のタグ",
    related: ["elastic", "plastic"],
  },
  { name: "electrical", desc: "電気解析関連のタグ", related: ["conductivity"] },
  { name: "density", desc: "密度プロパティ", related: ["mass"] },
  { name: "creep", desc: "クリープ解析用", related: ["time-dependent"] },
  { name: "damage", desc: "損傷モデル用", related: ["failure", "fracture"] },
];

const TAGS: StringEntity[] = TAG_DEFINITIONS.map((tag, i) => ({
  id: `tag-${i + 1}`,
  name: tag.name,
  body: `# ${tag.name}\n\n${tag.desc}\n\n関連タグ: ${tag.related.join(", ")}`,
  entityType: "Tag" as EntityType,
  sysTags: ["tag-definition"],
  userTags: tag.related,
  sysProps: { type: "tag" },
  userProps: {},
  remark: tag.desc,
  domain: "tag",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - i * 86400000).toISOString(),
}));

// ===== Template タイプのデータ =====
const TEMPLATE_DEFINITIONS = [
  {
    name: "線形弾性テンプレート",
    desc: "等方性線形弾性材料の基本テンプレート",
    body: `*Material, name=<NAME>\n*Elastic\n <E>, <nu>`,
  },
  {
    name: "熱弾性テンプレート",
    desc: "熱膨張を含む弾性材料テンプレート",
    body: `*Material, name=<NAME>\n*Elastic\n <E>, <nu>\n*Expansion\n <alpha>`,
  },
  {
    name: "弾塑性テンプレート",
    desc: "等方硬化を含む弾塑性材料テンプレート",
    body: `*Material, name=<NAME>\n*Elastic\n <E>, <nu>\n*Plastic\n <sigma_y>, 0.`,
  },
];

const TEMPLATES: StringEntity[] = TEMPLATE_DEFINITIONS.map((tmpl, i) => ({
  id: `tmpl-${i + 1}`,
  name: tmpl.name,
  body: tmpl.body,
  entityType: "Project" as EntityType,
  sysTags: ["template", "abaqus"],
  userTags: ["reusable"],
  sysProps: { type: "template" },
  userProps: {},
  remark: tmpl.desc,
  domain: "template",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - i * 86400000).toISOString(),
}));

// ===== Document タイプのデータ =====
const DOCUMENT_DEFINITIONS = [
  {
    name: "材料定義ガイド",
    desc: "Abaqusでの材料定義方法",
    body: `# 材料定義ガイド\n\nAbaqusで材料を定義する際の基本手順。\n\n1. *Material キーワードで材料名を指定\n2. 必要な物性値を追加\n3. 解析タイプに応じた追加設定`,
  },
  {
    name: "物性値単位規約",
    desc: "SI単位系での物性値記述規約",
    body: `# 単位規約\n\n- 長さ: mm\n- 質量: tonne\n- 時間: s\n- 応力: MPa\n- 密度: tonne/mm^3`,
  },
];

const DOCUMENTS: StringEntity[] = DOCUMENT_DEFINITIONS.map((doc, i) => ({
  id: `doc-${i + 1}`,
  name: doc.name,
  body: doc.body,
  entityType: "Project" as EntityType,
  sysTags: ["document", "guide"],
  userTags: ["reference"],
  sysProps: { type: "document" },
  userProps: {},
  remark: doc.desc,
  domain: "document",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - i * 86400000).toISOString(),
}));

// ===== カテゴリ・サブカテゴリ・グレード エンティティ =====
// ラベル付きRelationのターゲットとなるエンティティ

// カテゴリ
const CATEGORY_ENTITIES: StringEntity[] = [
  {
    id: "cat-metal",
    name: "金属",
    body: "材料カテゴリ: 金属材料",
    entityType: "Tag" as EntityType,
    sysTags: ["category"],
    userTags: [],
    sysProps: { type: "category" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "cat-resin",
    name: "樹脂",
    body: "材料カテゴリ: 樹脂材料",
    entityType: "Tag" as EntityType,
    sysTags: ["category"],
    userTags: [],
    sysProps: { type: "category" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "cat-ceramic",
    name: "セラミックス",
    body: "材料カテゴリ: セラミックス材料",
    entityType: "Tag" as EntityType,
    sysTags: ["category"],
    userTags: [],
    sysProps: { type: "category" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "cat-composite",
    name: "複合材料",
    body: "材料カテゴリ: 複合材料",
    entityType: "Tag" as EntityType,
    sysTags: ["category"],
    userTags: [],
    sysProps: { type: "category" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
];

// サブカテゴリ
const SUBCATEGORY_ENTITIES: StringEntity[] = [
  {
    id: "subcat-steel",
    name: "鉄鋼",
    body: "サブカテゴリ: 鉄鋼材料",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-stainless",
    name: "ステンレス",
    body: "サブカテゴリ: ステンレス鋼",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-aluminum",
    name: "アルミニウム",
    body: "サブカテゴリ: アルミニウム合金",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-copper",
    name: "銅",
    body: "サブカテゴリ: 銅・銅合金",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-thermoplastic",
    name: "熱可塑性",
    body: "サブカテゴリ: 熱可塑性樹脂",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-thermoset",
    name: "熱硬化性",
    body: "サブカテゴリ: 熱硬化性樹脂",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "subcat-oxide",
    name: "酸化物",
    body: "サブカテゴリ: 酸化物セラミックス",
    entityType: "Tag" as EntityType,
    sysTags: ["subcategory"],
    userTags: [],
    sysProps: { type: "subcategory" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
];

// グレード
const GRADE_ENTITIES: StringEntity[] = [
  {
    id: "grade-general-structural",
    name: "一般構造用",
    body: "グレード: 一般構造用",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-ferrite",
    name: "フェライト系",
    body: "グレード: フェライト系ステンレス",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-high-strength",
    name: "高強度",
    body: "グレード: 高強度",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-pure-copper",
    name: "純銅",
    body: "グレード: 純銅",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-general-purpose",
    name: "汎用",
    body: "グレード: 汎用",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-engineering",
    name: "エンプラ",
    body: "グレード: エンジニアリングプラスチック",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-adhesive",
    name: "接着用",
    body: "グレード: 接着用",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-high-purity",
    name: "高純度",
    body: "グレード: 高純度",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
  {
    id: "grade-stabilized",
    name: "安定化",
    body: "グレード: 安定化ジルコニア",
    entityType: "Tag" as EntityType,
    sysTags: ["grade"],
    userTags: [],
    sysProps: { type: "grade" },
    userProps: {},
    domain: "category",
    domainSource: "curation",
    domainConfidence: 1.0,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: BASE_DATE.toISOString(),
  },
];

// ===== プロパティグループ化検証用データ =====
// カテゴリ・サブカテゴリ・グレードはラベル付きRelationで表現
const PROPERTY_GROUP_TEST_DATA: StringEntity[] = [
  // 金属
  {
    id: "prop-test-1",
    name: "鉄鋼材料 SS400",
    body: "*Material, name=SS400\n*Elastic\n 200.e3, 0.3",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["structural"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 1 * 86400000).toISOString(),
  },
  {
    id: "prop-test-2",
    name: "ステンレス SUS430",
    body: "*Material, name=SUS430\n*Elastic\n 190.e3, 0.3",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["corrosion-resistant"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 2 * 86400000).toISOString(),
  },
  {
    id: "prop-test-3",
    name: "アルミ合金 A2024",
    body: "*Material, name=A2024\n*Elastic\n 73.e3, 0.33",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["lightweight"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 3 * 86400000).toISOString(),
  },
  {
    id: "prop-test-4",
    name: "銅合金 C1100",
    body: "*Material, name=C1100\n*Elastic\n 117.e3, 0.35",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["electrical"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 4 * 86400000).toISOString(),
  },
  // 樹脂
  {
    id: "prop-test-5",
    name: "ABS樹脂",
    body: "*Material, name=ABS\n*Elastic\n 2.3e3, 0.35",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["plastic"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 5 * 86400000).toISOString(),
  },
  {
    id: "prop-test-6",
    name: "ポリカーボネート",
    body: "*Material, name=PC\n*Elastic\n 2.4e3, 0.38",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["plastic", "transparent"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 6 * 86400000).toISOString(),
  },
  {
    id: "prop-test-7",
    name: "エポキシ樹脂",
    body: "*Material, name=Epoxy\n*Elastic\n 3.5e3, 0.35",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["thermoset"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 7 * 86400000).toISOString(),
  },
  // セラミックス
  {
    id: "prop-test-8",
    name: "アルミナ Al2O3",
    body: "*Material, name=Alumina\n*Elastic\n 370.e3, 0.22",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["ceramic", "insulator"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 8 * 86400000).toISOString(),
  },
  {
    id: "prop-test-9",
    name: "ジルコニア ZrO2",
    body: "*Material, name=Zirconia\n*Elastic\n 200.e3, 0.31",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["ceramic"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 9 * 86400000).toISOString(),
  },
  // 未分類
  {
    id: "prop-test-10",
    name: "未分類材料A",
    body: "*Material, name=UnknownA\n*Elastic\n 100.e3, 0.3",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: [],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "auto",
    domainConfidence: 0.5,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 10 * 86400000).toISOString(),
  },
  {
    id: "prop-test-11",
    name: "未分類材料B",
    body: "*Material, name=UnknownB\n*Elastic\n 150.e3, 0.28",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: [],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "auto",
    domainConfidence: 0.5,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 11 * 86400000).toISOString(),
  },
  // 複合材料
  {
    id: "prop-test-12",
    name: "複合材料 CFRP",
    body: "*Material, name=CFRP\n*Elastic, type=ortho\n 135.e3, 10.e3, 10.e3",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["composite"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 12 * 86400000).toISOString(),
  },
  {
    id: "prop-test-13",
    name: "複合材料 GFRP",
    body: "*Material, name=GFRP\n*Elastic, type=ortho\n 45.e3, 12.e3, 12.e3",
    entityType: "Material" as EntityType,
    sysTags: ["material"],
    userTags: ["composite"],
    sysProps: {},
    userProps: {},
    domain: "abaqus_inp",
    domainSource: "curation",
    domainConfidence: 0.9,
    createdAt: BASE_DATE.toISOString(),
    updatedAt: new Date(BASE_DATE.getTime() - 13 * 86400000).toISOString(),
  },
];

// ===== 多様なフォーマットのProjectデータ =====

const CSV_PROJECT: StringEntity = {
  id: "proj-csv-1",
  name: "材料物性値一覧表",
  body: `name,density,youngs_modulus,poisson_ratio,yield_strength,tensile_strength
SS400,7.85e-9,200.e3,0.3,235.,400.
SUS304,7.93e-9,193.e3,0.29,205.,520.
A5052,2.68e-9,70.e3,0.33,65.,195.
Ti-6Al-4V,4.43e-9,113.e3,0.34,880.,950.
Inconel718,8.19e-9,200.e3,0.29,1035.,1240.
Cu-ETP,8.94e-9,117.e3,0.35,69.,220.
PEEK,1.30e-9,4.1e3,0.40,91.,100.
CFRP,1.55e-9,135.e3,0.30,1500.,1800.`,
  entityType: "Project" as EntityType,
  sysTags: ["dataset", "csv"],
  userTags: ["material-properties", "reference"],
  sysProps: { extension: "csv", format: "csv" },
  userProps: { usage: "参照用" },
  remark: "主要材料の物性値一覧（CSV形式）",
  domain: "csv",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - 1 * 86400000).toISOString(),
};

const JSON_PROJECT: StringEntity = {
  id: "proj-json-1",
  name: "解析条件テンプレート集",
  body: JSON.stringify(
    {
      templates: [
        {
          name: "静的構造解析",
          type: "static",
          solver: "Abaqus/Standard",
          steps: [
            {
              name: "Load",
              type: "Static,General",
              nlgeom: "YES",
              timePeriod: 1.0,
            },
          ],
          output: ["S", "U", "RF"],
        },
        {
          name: "モーダル解析",
          type: "frequency",
          solver: "Abaqus/Standard",
          steps: [
            {
              name: "Frequency",
              type: "Frequency",
              numEigen: 10,
              normalization: "DISPLACEMENT",
            },
          ],
          output: ["U"],
        },
        {
          name: "熱伝導解析",
          type: "heat_transfer",
          solver: "Abaqus/Standard",
          steps: [
            { name: "HeatTransfer", type: "Heat Transfer", timePeriod: 100.0 },
          ],
          output: ["NT", "HFL"],
        },
      ],
    },
    null,
    2,
  ),
  entityType: "Project" as EntityType,
  sysTags: ["template", "json"],
  userTags: ["analysis-config", "reusable"],
  sysProps: { extension: "json", format: "json" },
  userProps: { usage: "解析設定" },
  remark: "各種解析タイプの条件テンプレート（JSON形式）",
  domain: "json",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - 2 * 86400000).toISOString(),
};

const YAML_PROJECT: StringEntity = {
  id: "proj-yaml-1",
  name: "材料試験手順書",
  body: `# 材料試験手順書
project: mat-db
version: "1.0"

tests:
  - name: 引張試験
    standard: JIS Z 2241
    specimen:
      type: 平板
      gauge_length: 50mm
      width: 12.5mm
    conditions:
      temperature: 23°C
      strain_rate: 0.001/s
    outputs:
      - 応力-ひずみ曲線
      - ヤング率
      - 耐力
      - 引張強度
      - 伸び

  - name: 硬さ試験
    standard: JIS Z 2244
    method: ビッカース
    conditions:
      load: 9.807N
      holding_time: 15s
    outputs:
      - ビッカース硬さ HV

  - name: シャルピー衝撃試験
    standard: JIS Z 2242
    specimen:
      type: Vノッチ
      notch_depth: 2mm
    conditions:
      temperatures: [-40, -20, 0, 23]
    outputs:
      - 吸収エネルギー
      - 遷移温度曲線`,
  entityType: "Project" as EntityType,
  sysTags: ["procedure", "yaml"],
  userTags: ["testing", "standard"],
  sysProps: { extension: "yaml", format: "yaml" },
  userProps: { usage: "試験管理" },
  remark: "材料試験の標準手順書（YAML形式）",
  domain: "yaml",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - 3 * 86400000).toISOString(),
};

const MD_PROJECT: StringEntity = {
  id: "proj-md-1",
  name: "CAE解析レポートテンプレート",
  body: `# CAE解析レポート

## 1. 解析概要

| 項目 | 内容 |
|------|------|
| 解析名 | (解析名を記入) |
| 解析種別 | 静的構造解析 / モーダル解析 / 熱解析 |
| ソルバー | Abaqus/Standard |
| 解析日 | YYYY-MM-DD |

## 2. モデル情報

### 2.1 形状
- 形状ソース: CADモデル
- 簡略化: (簡略化内容を記入)

### 2.2 メッシュ
- 要素タイプ: C3D10 (2次テトラ)
- 節点数: (節点数)
- 要素数: (要素数)

### 2.3 材料
使用した材料物性値は以下の通り:

| 材料名 | ヤング率 [MPa] | ポアソン比 | 密度 [tonne/mm³] |
|--------|---------------|-----------|-----------------|
| SS400  | 200,000       | 0.3       | 7.85e-9         |

## 3. 境界条件
- **拘束**: (拘束条件)
- **荷重**: (荷重条件)

## 4. 結果

### 4.1 変位
- 最大変位: (値) mm

### 4.2 応力
- 最大ミーゼス応力: (値) MPa
- 安全率: (値)

## 5. 結論
(解析結論を記入)`,
  entityType: "Project" as EntityType,
  sysTags: ["report", "markdown"],
  userTags: ["template", "documentation"],
  sysProps: { extension: "md", format: "markdown" },
  userProps: { usage: "文書管理" },
  remark: "CAE解析レポートのMarkdownテンプレート",
  domain: "markdown",
  domainSource: "curation",
  domainConfidence: 1.0,
  createdAt: BASE_DATE.toISOString(),
  updatedAt: new Date(BASE_DATE.getTime() - 4 * 86400000).toISOString(),
};

const FORMAT_PROJECTS: StringEntity[] = [
  CSV_PROJECT,
  JSON_PROJECT,
  YAML_PROJECT,
  MD_PROJECT,
];

/**
 * MOCKデータ
 * Material, Tag, Projectの3種類を含む
 */
export const MOCK_ENTITIES: StringEntity[] = [
  ...MATERIALS,
  ...TAGS,
  ...TEMPLATES,
  ...DOCUMENTS,
  ...CATEGORY_ENTITIES,
  ...SUBCATEGORY_ENTITIES,
  ...GRADE_ENTITIES,
  ...PROPERTY_GROUP_TEST_DATA,
  ...FORMAT_PROJECTS,
];

// ===== Mock Relation 定義 =====

export type MockRelation = {
  id: string;
  label: string;
  entity1Id: string;
  entity2Id: string;
  createdAt: string;
};

export const MOCK_RELATIONS: MockRelation[] = [
  // 材料間の関連
  {
    id: "rel-1",
    label: "similar_to",
    entity1Id: "mat-1",
    entity2Id: "mat-2",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-2",
    label: "similar_to",
    entity1Id: "mat-3",
    entity2Id: "mat-4",
    createdAt: BASE_DATE.toISOString(),
  },
  // 材料とタグの関連
  {
    id: "rel-3",
    label: "tagged_with",
    entity1Id: "mat-1",
    entity2Id: "tag-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-4",
    label: "tagged_with",
    entity1Id: "mat-2",
    entity2Id: "tag-2",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-5",
    label: "tagged_with",
    entity1Id: "mat-3",
    entity2Id: "tag-2",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-6",
    label: "tagged_with",
    entity1Id: "mat-5",
    entity2Id: "tag-1",
    createdAt: BASE_DATE.toISOString(),
  },
  // 材料とテンプレートの関連
  {
    id: "rel-7",
    label: "uses_template",
    entity1Id: "mat-1",
    entity2Id: "tmpl-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-8",
    label: "uses_template",
    entity1Id: "mat-2",
    entity2Id: "tmpl-3",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-9",
    label: "uses_template",
    entity1Id: "mat-5",
    entity2Id: "tmpl-2",
    createdAt: BASE_DATE.toISOString(),
  },
  // プロジェクトとドキュメントの関連
  {
    id: "rel-10",
    label: "references",
    entity1Id: "tmpl-1",
    entity2Id: "doc-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-11",
    label: "references",
    entity1Id: "tmpl-2",
    entity2Id: "doc-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-12",
    label: "references",
    entity1Id: "doc-1",
    entity2Id: "doc-2",
    createdAt: BASE_DATE.toISOString(),
  },
  // CSV物性値とMaterial間の関連
  {
    id: "rel-13",
    label: "data_source",
    entity1Id: "prop-test-1",
    entity2Id: "proj-csv-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-14",
    label: "data_source",
    entity1Id: "prop-test-2",
    entity2Id: "proj-csv-1",
    createdAt: BASE_DATE.toISOString(),
  },
  // レポートテンプレートと解析テンプレートの関連
  {
    id: "rel-15",
    label: "related_to",
    entity1Id: "proj-md-1",
    entity2Id: "proj-json-1",
    createdAt: BASE_DATE.toISOString(),
  },
  // 試験手順書と材料の関連
  {
    id: "rel-16",
    label: "applies_to",
    entity1Id: "proj-yaml-1",
    entity2Id: "prop-test-1",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "rel-17",
    label: "applies_to",
    entity1Id: "proj-yaml-1",
    entity2Id: "prop-test-3",
    createdAt: BASE_DATE.toISOString(),
  },
  // 複合材料間の関連
  {
    id: "rel-18",
    label: "similar_to",
    entity1Id: "prop-test-12",
    entity2Id: "prop-test-13",
    createdAt: BASE_DATE.toISOString(),
  },
  // セラミックス間の関連
  {
    id: "rel-19",
    label: "similar_to",
    entity1Id: "prop-test-8",
    entity2Id: "prop-test-9",
    createdAt: BASE_DATE.toISOString(),
  },
  // タグ間の関連
  {
    id: "rel-20",
    label: "related_to",
    entity1Id: "tag-1",
    entity2Id: "tag-3",
    createdAt: BASE_DATE.toISOString(),
  },

  // ===== ラベル付きRelation: カテゴリ =====
  // 金属
  {
    id: "lrel-cat-1",
    label: "カテゴリ",
    entity1Id: "prop-test-1",
    entity2Id: "cat-metal",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-2",
    label: "カテゴリ",
    entity1Id: "prop-test-2",
    entity2Id: "cat-metal",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-3",
    label: "カテゴリ",
    entity1Id: "prop-test-3",
    entity2Id: "cat-metal",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-4",
    label: "カテゴリ",
    entity1Id: "prop-test-4",
    entity2Id: "cat-metal",
    createdAt: BASE_DATE.toISOString(),
  },
  // 樹脂
  {
    id: "lrel-cat-5",
    label: "カテゴリ",
    entity1Id: "prop-test-5",
    entity2Id: "cat-resin",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-6",
    label: "カテゴリ",
    entity1Id: "prop-test-6",
    entity2Id: "cat-resin",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-7",
    label: "カテゴリ",
    entity1Id: "prop-test-7",
    entity2Id: "cat-resin",
    createdAt: BASE_DATE.toISOString(),
  },
  // セラミックス
  {
    id: "lrel-cat-8",
    label: "カテゴリ",
    entity1Id: "prop-test-8",
    entity2Id: "cat-ceramic",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-9",
    label: "カテゴリ",
    entity1Id: "prop-test-9",
    entity2Id: "cat-ceramic",
    createdAt: BASE_DATE.toISOString(),
  },
  // 複合材料
  {
    id: "lrel-cat-10",
    label: "カテゴリ",
    entity1Id: "prop-test-12",
    entity2Id: "cat-composite",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-cat-11",
    label: "カテゴリ",
    entity1Id: "prop-test-13",
    entity2Id: "cat-composite",
    createdAt: BASE_DATE.toISOString(),
  },

  // ===== ラベル付きRelation: サブカテゴリ =====
  {
    id: "lrel-sub-1",
    label: "サブカテゴリ",
    entity1Id: "prop-test-1",
    entity2Id: "subcat-steel",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-2",
    label: "サブカテゴリ",
    entity1Id: "prop-test-2",
    entity2Id: "subcat-stainless",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-3",
    label: "サブカテゴリ",
    entity1Id: "prop-test-3",
    entity2Id: "subcat-aluminum",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-4",
    label: "サブカテゴリ",
    entity1Id: "prop-test-4",
    entity2Id: "subcat-copper",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-5",
    label: "サブカテゴリ",
    entity1Id: "prop-test-5",
    entity2Id: "subcat-thermoplastic",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-6",
    label: "サブカテゴリ",
    entity1Id: "prop-test-6",
    entity2Id: "subcat-thermoplastic",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-7",
    label: "サブカテゴリ",
    entity1Id: "prop-test-7",
    entity2Id: "subcat-thermoset",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-8",
    label: "サブカテゴリ",
    entity1Id: "prop-test-8",
    entity2Id: "subcat-oxide",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-sub-9",
    label: "サブカテゴリ",
    entity1Id: "prop-test-9",
    entity2Id: "subcat-oxide",
    createdAt: BASE_DATE.toISOString(),
  },

  // ===== ラベル付きRelation: グレード =====
  {
    id: "lrel-grd-1",
    label: "グレード",
    entity1Id: "prop-test-1",
    entity2Id: "grade-general-structural",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-2",
    label: "グレード",
    entity1Id: "prop-test-2",
    entity2Id: "grade-ferrite",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-3",
    label: "グレード",
    entity1Id: "prop-test-3",
    entity2Id: "grade-high-strength",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-4",
    label: "グレード",
    entity1Id: "prop-test-4",
    entity2Id: "grade-pure-copper",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-5",
    label: "グレード",
    entity1Id: "prop-test-5",
    entity2Id: "grade-general-purpose",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-6",
    label: "グレード",
    entity1Id: "prop-test-6",
    entity2Id: "grade-engineering",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-7",
    label: "グレード",
    entity1Id: "prop-test-7",
    entity2Id: "grade-adhesive",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-8",
    label: "グレード",
    entity1Id: "prop-test-8",
    entity2Id: "grade-high-purity",
    createdAt: BASE_DATE.toISOString(),
  },
  {
    id: "lrel-grd-9",
    label: "グレード",
    entity1Id: "prop-test-9",
    entity2Id: "grade-stabilized",
    createdAt: BASE_DATE.toISOString(),
  },
];

/**
 * IDでエンティティを取得
 */
export function getMockEntityById(id: string): StringEntity | undefined {
  return MOCK_ENTITIES.find((e) => e.id === id);
}

/**
 * 検索・フィルタリング
 */
export function searchMockEntities(options: {
  nameQuery?: string;
  tags?: string[];
}): StringEntity[] {
  return searchEntities(MOCK_ENTITIES, options);
}
