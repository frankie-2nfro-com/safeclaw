import json
import re
import psycopg2
import os

from libs.base_skill import BaseSkill

# LLM sometimes returns "1.勝萬金" or "2. 團長好" - strip leading number prefix for lookup/storage
_HORSE_NAME_PREFIX = re.compile(r"^\d+[\.\s]+")


def _normalize_horse_name(name: str) -> str:
    """Strip leading 'N.' or 'N ' from horse name. e.g. '1.勝萬金' -> '勝萬金'."""
    return _HORSE_NAME_PREFIX.sub("", name).strip()


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
        race_date = params.get("race_date", "")
        race_no = params.get("race_no", "")

        print(f"mongchoi_update::{race_date}::{race_no} -> Update Race Analysis", flush=True)
        print(params, flush=True)
        print(flush=True)

        artifact = params.get("artifact", {})
        artifact_content = artifact.get("content", artifact) if isinstance(artifact, dict) else {}
        # content may be a JSON string (from artifact.json) or already a dict
        if isinstance(artifact_content, str):
            try:
                artifact_content = json.loads(artifact_content)
            except json.JSONDecodeError:
                artifact_content = {}
        if not isinstance(artifact_content, dict):
            artifact_content = {}
        print(f"  -> {len(artifact_content)} horses", flush=True)


        conn = self._db_connect()
        horse_hno = 0
        try:
            batch_update_sql = f"INSERT INTO race_horse_analysis (race_date, race_no, horse_name, horse_analysis, hno) VALUES "
            for raw_name, horse_analysis in artifact_content.items():
                horse_name = _normalize_horse_name(raw_name)
                horse_name_escaped = horse_name.replace("'", "\\'")

                # check if horse_name is in this race to prevent ai wrong returning
                check_sql = f"SELECT hno FROM race_horse WHERE race_date='{race_date}' AND race_no={race_no} AND hname='{horse_name_escaped}'"
                cursor = conn.cursor()
                cursor.execute(check_sql)
                result = cursor.fetchone()
                if result:
                    horse_hno = result[0]
                else:
                    raise Exception(f"Horse {horse_name} not found in this race - {check_sql}")
                cursor.close()

                horse_analysis_escaped = horse_analysis.replace("'", "\\'")
                batch_update_sql += f"('{race_date}', {race_no}, '{horse_name_escaped}', '{horse_analysis_escaped}', {horse_hno}),"
            batch_update_sql = batch_update_sql.rstrip(",")
            batch_update_sql += f" ON CONFLICT (race_date, race_no, horse_name) DO UPDATE SET horse_analysis=EXCLUDED.horse_analysis, hno=EXCLUDED.hno, modify_dt=now();"
            
            # execute the batch update sql
            cursor = conn.cursor()
            cursor.execute(batch_update_sql)
            conn.commit()
            cursor.close()
            return {"status": "Executed", "text": "Mongchoi update executed."}
        except Exception as e:
            print(f"Error: {e}", flush=True)
            return {"status": "Failed", "text": f"Error: {e}"}
        finally:
            if conn:
                conn.close()

        


            

