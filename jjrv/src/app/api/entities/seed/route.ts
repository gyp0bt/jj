import { NextResponse } from "next/server";
import { getAuthPayload, hashPassword } from "@/lib/auth";
import {
  createRelation,
  getAllEntities,
  getEntityById,
  getEntityCount,
  getRelationsByEntityId,
  upsertEntity,
} from "@/lib/entity-repository";
import { addFavorite } from "@/lib/entity-stats-repository";
import { MOCK_ENTITIES, MOCK_RELATIONS } from "@/lib/mock-data";
import type { StringEntity } from "@/lib/types";
import {
  createUser,
  getAllUsers,
  getUserByUsername,
} from "@/lib/user-repository";

// POST /api/entities/seed - 初期データ投入
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const source = body.source as "mock" | "import" | undefined;
    const entities = body.entities as StringEntity[] | undefined;

    let admin = await getUserByUsername("admin");
    if (!admin) {
      const passwordHash = await hashPassword("admin123");
      const id = crypto.randomUUID();
      const created = await createUser(
        id,
        "admin",
        passwordHash,
        "管理者",
        "admin",
      );
      admin = { ...created, passwordHash };
    }

    const extraUsernames = ["user1", "user2", "user3", "user4", "user5"];
    for (const username of extraUsernames) {
      const existing = await getUserByUsername(username);
      if (existing) continue;
      const passwordHash = await hashPassword("user123");
      const id = crypto.randomUUID();
      await createUser(
        id,
        username,
        passwordHash,
        username.toUpperCase(),
        "user",
      );
    }

    let seedEntities: StringEntity[] = [];

    if (source === "mock" || (!source && !entities)) {
      // MOCKデータを投入
      seedEntities = MOCK_ENTITIES;
    } else if (entities && Array.isArray(entities)) {
      // 渡されたエンティティを投入（localStorageからの移行用）
      seedEntities = entities;
    }

    let created = 0;
    let updated = 0;
    for (const entity of seedEntities) {
      try {
        const payload = { ...entity, createdBy: admin.id };
        const existed = await getEntityById(payload.id);
        await upsertEntity(payload);
        if (existed) {
          updated++;
        } else {
          created++;
        }
      } catch (_e) {
        // 既存のIDがある場合はスキップ
        console.warn(`Entity ${entity.id} already exists, skipping`);
      }
    }

    const allEntities = await getAllEntities();
    const allUsers = await getAllUsers();
    for (const entity of allEntities) {
      const favoriteCount = Math.floor(Math.random() * 4);
      const shuffled = [...allUsers].sort(() => Math.random() - 0.5);
      for (const user of shuffled.slice(0, favoriteCount)) {
        await addFavorite(user.id, entity.id);
      }
    }

    // Relation投入
    let relationsCreated = 0;
    if (source === "mock" || (!source && !entities)) {
      for (const rel of MOCK_RELATIONS) {
        try {
          const existing = await getRelationsByEntityId(rel.entity1Id);
          const alreadyExists = existing.some(
            (r) =>
              (r.entity1Id === rel.entity1Id &&
                r.entity2Id === rel.entity2Id) ||
              (r.entity1Id === rel.entity2Id && r.entity2Id === rel.entity1Id),
          );
          if (!alreadyExists) {
            await createRelation(rel);
            relationsCreated++;
          }
        } catch (_e) {
          // skip duplicates
        }
      }
    }

    return NextResponse.json({
      message: `${created}件のデータを投入しました`,
      count: created,
      updated,
      relationsCreated,
      adminUser: admin.username,
      extraUsers: extraUsernames,
    });
  } catch (error) {
    console.error("POST /api/entities/seed error:", error);
    return NextResponse.json(
      { error: "データ投入に失敗しました" },
      { status: 500 },
    );
  }
}

// GET /api/entities/seed - シード状態確認
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const count = await getEntityCount();
    const entities = await getAllEntities();
    return NextResponse.json({
      count,
      hasData: count > 0,
      mockAvailable: MOCK_ENTITIES.length,
      entities: entities.slice(0, 5), // プレビュー用に最初の5件
    });
  } catch (error) {
    console.error("GET /api/entities/seed error:", error);
    return NextResponse.json(
      { error: "状態確認に失敗しました" },
      { status: 500 },
    );
  }
}
