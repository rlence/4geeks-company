-- Aplicar con identidad de migración. La API utiliza inventory_app, nunca el dueño.
-- La creación del login/contraseña es un paso separado; no hay secretos en este archivo.
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'inventory_app') THEN
    CREATE ROLE inventory_app NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
  END IF;
END $$;
CREATE SCHEMA inventory;
REVOKE ALL ON SCHEMA inventory FROM PUBLIC;
GRANT USAGE ON SCHEMA inventory TO inventory_app;
CREATE TABLE inventory.ingredients (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK (id <= 9007199254740991),
 name text NOT NULL CHECK (char_length(btrim(name)) BETWEEN 1 AND 160),
 sku text NOT NULL UNIQUE CHECK (char_length(btrim(sku)) BETWEEN 1 AND 80),
 unit text NOT NULL CHECK (char_length(btrim(unit)) BETWEEN 1 AND 40),
 category text NOT NULL CHECK (category IN ('meat','produce','sauce','beverage','packaging','cleaning')),
 country text NOT NULL CHECK (country IN ('CO','US'))
);
CREATE TABLE inventory.entries (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK (id <= 9007199254740991),
 ingredient_id bigint NOT NULL REFERENCES inventory.ingredients(id) ON DELETE RESTRICT,
 quantity numeric(18,6) NOT NULL CHECK (quantity > 0 AND quantity < 'Infinity'::numeric),
 supplier_name text NOT NULL CHECK (char_length(btrim(supplier_name)) BETWEEN 1 AND 160),
 location_id integer NOT NULL CHECK (location_id BETWEEN 1 AND 14),
 user_uuid text NOT NULL CHECK (char_length(btrim(user_uuid)) BETWEEN 1 AND 80),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE inventory.exits (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK (id <= 9007199254740991),
 ingredient_id bigint NOT NULL REFERENCES inventory.ingredients(id) ON DELETE RESTRICT,
 quantity numeric(18,6) NOT NULL CHECK (quantity > 0 AND quantity < 'Infinity'::numeric),
 reason text NOT NULL CHECK (reason IN ('consumption','waste')),
 location_id integer NOT NULL CHECK (location_id BETWEEN 1 AND 14),
 user_uuid text NOT NULL CHECK (char_length(btrim(user_uuid)) BETWEEN 1 AND 80),
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE inventory.seed_runs (
 version text PRIMARY KEY,
 applied_at timestamptz NOT NULL DEFAULT now(),
 user_uuid text NOT NULL
);
CREATE INDEX entries_ingredient ON inventory.entries(ingredient_id);
CREATE INDEX exits_ingredient ON inventory.exits(ingredient_id);
CREATE INDEX entries_date ON inventory.entries(created_at DESC, id DESC);
CREATE INDEX exits_date ON inventory.exits(created_at DESC, id DESC);
REVOKE ALL ON ALL TABLES IN SCHEMA inventory FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA inventory FROM PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA inventory TO inventory_app;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA inventory TO inventory_app;
-- FOR UPDATE requiere privilegio UPDATE. Solo id, y RLS impide actualizar valores.
GRANT UPDATE(id) ON inventory.ingredients TO inventory_app;
ALTER TABLE inventory.ingredients ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory.entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory.exits ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory.seed_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY ingredients_read ON inventory.ingredients FOR SELECT TO inventory_app USING (true);
CREATE POLICY ingredients_insert ON inventory.ingredients FOR INSERT TO inventory_app WITH CHECK (true);
CREATE POLICY ingredients_lock ON inventory.ingredients FOR UPDATE TO inventory_app USING (true) WITH CHECK (false);
CREATE POLICY entries_read ON inventory.entries FOR SELECT TO inventory_app USING (true);
CREATE POLICY entries_insert ON inventory.entries FOR INSERT TO inventory_app WITH CHECK (true);
CREATE POLICY exits_read ON inventory.exits FOR SELECT TO inventory_app USING (true);
CREATE POLICY exits_insert ON inventory.exits FOR INSERT TO inventory_app WITH CHECK (true);
CREATE POLICY seed_read ON inventory.seed_runs FOR SELECT TO inventory_app USING (true);
CREATE POLICY seed_insert ON inventory.seed_runs FOR INSERT TO inventory_app WITH CHECK (true);
-- Denegar también grants por defecto del proveedor si existen esos roles.
DO $$ DECLARE r text; BEGIN
 FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP
  IF EXISTS (SELECT FROM pg_roles WHERE rolname=r) THEN
   EXECUTE format('REVOKE ALL ON SCHEMA inventory FROM %I',r);
   EXECUTE format('REVOKE ALL ON ALL TABLES IN SCHEMA inventory FROM %I',r);
   EXECUTE format('REVOKE ALL ON ALL SEQUENCES IN SCHEMA inventory FROM %I',r);
  END IF;
 END LOOP;
END $$;
