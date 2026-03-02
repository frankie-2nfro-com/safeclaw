import json
import psycopg2
import os

from libs.base_skill import BaseSkill


class MongchoiUpdateSkill(BaseSkill):
    def _db_connect(self):
        """Connect to Mongchoi DB using env: MONGCHOI_DB_HOST, MONGCHOI_DB_DATABASE, MONGCHOI_DB_USER, MONGCHOI_DB_PASSWORD."""
        host = os.getenv("MONGCHOI_DB_HOST")
        database = os.getenv("MONGCHOI_DB_DATABASE")
        user = os.getenv("MONGCHOI_DB_USER")
        password = os.getenv("MONGCHOI_DB_PASSWORD")
        if not all([host, database, user, password]):
            raise ValueError("MONGCHOI_DB_HOST, MONGCHOI_DB_DATABASE, MONGCHOI_DB_USER, MONGCHOI_DB_PASSWORD must be set in .env")
        return psycopg2.connect(host=host, database=database, user=user, password=password)

    def execute(self, params: dict):
        request_info = {"action": "MONGCHOI_UPDATE", "params": params}

        artifact = params.get("artifact", {})
        artifact_content_str = artifact["content"]
        artifact_content = json.loads(artifact_content_str)

        race_date = params.get("race_date", "")
        race_no = params.get("race_no", "")

        batch_update_sql = f"INSERT INTO race_horse_analysis (race_date, race_no, horse_name, horse_analysis) VALUES "
        for horse_name, horse_analysis in artifact_content.items():
            # need to escape the single quotes in the horse_name and horse_analysis
            horse_name = horse_name.replace("'", "\\'")
            horse_analysis = horse_analysis.replace("'", "\\'")
            batch_update_sql += f"('{race_date}', {race_no}, '{horse_name}', '{horse_analysis}'),"
        batch_update_sql = batch_update_sql.rstrip(",")
        batch_update_sql += f" ON CONFLICT (race_date, race_no, horse_name) DO UPDATE SET horse_analysis=EXCLUDED.horse_analysis, modify_dt=now();"
        print(batch_update_sql)

        # execute the batch update sql 
        conn = None
        try:
            conn = self._db_connect()
            cursor = conn.cursor()
            cursor.execute(batch_update_sql)
            conn.commit()
            cursor.close()
            return {"status": "Executed", "text": "Mongchoi update executed."}
        except Exception as e:
            print(f"Error: {e}")
            return {"status": "Failed", "text": f"Error: {e}"}
        finally:
            if conn:
                conn.close()
