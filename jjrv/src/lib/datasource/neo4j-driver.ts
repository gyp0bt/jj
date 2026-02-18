import neo4j, { type Driver, type Session } from "neo4j-driver";

let driver: Driver | null = null;

type Neo4jConfig = {
  uri: string;
  user: string;
  password: string;
};

function getConfig(): Neo4jConfig {
  return {
    uri: process.env.NEO4J_URI || "bolt://localhost:7687",
    user: process.env.NEO4J_USER || "neo4j",
    password: process.env.NEO4J_PASSWORD || "password",
  };
}

export function getDriver(): Driver {
  if (driver) return driver;
  const config = getConfig();
  driver = neo4j.driver(
    config.uri,
    neo4j.auth.basic(config.user, config.password),
  );
  return driver;
}

export function getSession(): Session {
  return getDriver().session();
}

export async function closeDriver(): Promise<void> {
  if (driver) {
    await driver.close();
    driver = null;
  }
}

export async function verifyConnection(): Promise<boolean> {
  const session = getSession();
  try {
    await session.run("RETURN 1");
    return true;
  } catch {
    return false;
  } finally {
    await session.close();
  }
}
