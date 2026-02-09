import { getDb } from "./db";
import type { AttachedDocument, Document } from "./types";

type DocumentRow = {
  id: number;
  name: string;
  relative_path: string;
  mime_type: string | null;
  size: number | null;
  description: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

type EntityDocumentRow = {
  entity_id: string;
  document_id: number;
  relative_path: string;
  created_at: string;
};

function toDocument(row: DocumentRow): Document {
  return {
    id: row.id,
    name: row.name,
    relativePath: row.relative_path,
    mimeType: row.mime_type,
    size: row.size,
    description: row.description,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

export async function createDocument(
  doc: Omit<Document, "id" | "createdAt" | "updatedAt">,
): Promise<Document> {
  const db = await getDb();
  const now = new Date().toISOString();

  await db.run(
    `INSERT INTO documents (name, relative_path, mime_type, size, description, created_by, created_at, updated_at)
     VALUES (@name, @relativePath, @mimeType, @size, @description, @createdBy, @createdAt, @updatedAt)`,
    {
      name: doc.name,
      relativePath: doc.relativePath,
      mimeType: doc.mimeType ?? null,
      size: doc.size ?? null,
      description: doc.description ?? null,
      createdBy: doc.createdBy ?? null,
      createdAt: now,
      updatedAt: now,
    },
  );

  const row = await db.get<DocumentRow>(
    `SELECT * FROM documents WHERE relative_path = @relativePath ORDER BY id DESC LIMIT 1`,
    { relativePath: doc.relativePath },
  );

  if (!row) {
    throw new Error("Failed to create document");
  }

  return toDocument(row);
}

export async function getDocumentById(id: number): Promise<Document | null> {
  const db = await getDb();
  const row = await db.get<DocumentRow>(
    `SELECT * FROM documents WHERE id = @id`,
    { id },
  );
  return row ? toDocument(row) : null;
}

export async function getDocumentByPath(
  relativePath: string,
): Promise<Document | null> {
  const db = await getDb();
  const row = await db.get<DocumentRow>(
    `SELECT * FROM documents WHERE relative_path = @relativePath`,
    { relativePath },
  );
  return row ? toDocument(row) : null;
}

export async function getAllDocuments(): Promise<Document[]> {
  const db = await getDb();
  const rows = await db.all<DocumentRow>(
    `SELECT * FROM documents ORDER BY created_at DESC`,
  );
  return rows.map(toDocument);
}

export async function updateDocument(
  id: number,
  updates: Partial<Omit<Document, "id" | "createdAt" | "updatedAt">>,
): Promise<Document | null> {
  const db = await getDb();
  const now = new Date().toISOString();

  const fields: string[] = [];
  const params: Record<string, unknown> = { id };

  if (updates.name !== undefined) {
    fields.push("name = @name");
    params.name = updates.name;
  }
  if (updates.relativePath !== undefined) {
    fields.push("relative_path = @relativePath");
    params.relativePath = updates.relativePath;
  }
  if (updates.mimeType !== undefined) {
    fields.push("mime_type = @mimeType");
    params.mimeType = updates.mimeType;
  }
  if (updates.size !== undefined) {
    fields.push("size = @size");
    params.size = updates.size;
  }
  if (updates.description !== undefined) {
    fields.push("description = @description");
    params.description = updates.description;
  }

  if (fields.length === 0) {
    return getDocumentById(id);
  }

  fields.push("updated_at = @updatedAt");
  params.updatedAt = now;

  await db.run(
    `UPDATE documents SET ${fields.join(", ")} WHERE id = @id`,
    params,
  );

  return getDocumentById(id);
}

export async function deleteDocument(id: number): Promise<boolean> {
  const db = await getDb();
  const result = await db.run(`DELETE FROM documents WHERE id = @id`, { id });
  return result.changes > 0;
}

// エンティティとドキュメントの関連付け

export async function attachDocumentToEntity(
  entityId: string,
  documentId: number,
  relativePath: string,
): Promise<void> {
  const db = await getDb();
  const now = new Date().toISOString();

  await db.run(
    `INSERT OR REPLACE INTO entity_documents (entity_id, document_id, relative_path, created_at)
     VALUES (@entityId, @documentId, @relativePath, @createdAt)`,
    {
      entityId,
      documentId,
      relativePath,
      createdAt: now,
    },
  );
}

export async function detachDocumentFromEntity(
  entityId: string,
  documentId: number,
): Promise<boolean> {
  const db = await getDb();
  const result = await db.run(
    `DELETE FROM entity_documents WHERE entity_id = @entityId AND document_id = @documentId`,
    { entityId, documentId },
  );
  return result.changes > 0;
}

export async function getAttachedDocuments(
  entityId: string,
): Promise<AttachedDocument[]> {
  const db = await getDb();
  const rows = await db.all<EntityDocumentRow>(
    `SELECT * FROM entity_documents WHERE entity_id = @entityId`,
    { entityId },
  );
  return rows.map((row) => ({
    relativePath: row.relative_path,
    documentId: row.document_id,
  }));
}

export async function getDocumentsForEntity(
  entityId: string,
): Promise<Document[]> {
  const db = await getDb();
  const rows = await db.all<DocumentRow>(
    `SELECT d.* FROM documents d
     INNER JOIN entity_documents ed ON d.id = ed.document_id
     WHERE ed.entity_id = @entityId
     ORDER BY d.created_at DESC`,
    { entityId },
  );
  return rows.map(toDocument);
}

export async function getEntitiesForDocument(
  documentId: number,
): Promise<string[]> {
  const db = await getDb();
  const rows = await db.all<{ entity_id: string }>(
    `SELECT entity_id FROM entity_documents WHERE document_id = @documentId`,
    { documentId },
  );
  return rows.map((row) => row.entity_id);
}
