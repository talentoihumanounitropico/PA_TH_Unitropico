import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.database import SessionLocal
from src.models.entities import PlanMacro, Policy, StrategicItem, Activity, Task
from src.services.calculations import CalculationService

def normalize(items):
    total = sum(i.weight for i in items)
    if total > 100.001:
        print(f"  [!] Suma excede 100% ({total}%). Normalizando proporcionalmente...")
        for i in items:
            i.weight = (i.weight / total) * 100.0
            print(f"    -> Nuevo peso asignado: {i.weight:.2f}%")
        return True
    return False

def main():
    db = SessionLocal()
    try:
        changed = False
        print("Iniciando auditoría de pesos en la base de datos...\n")
        
        # 1. Macro -> Policies
        macros = db.query(PlanMacro).all()
        for m in macros:
            print(f"Revisando Macro: {m.name}")
            if normalize(m.policies): changed = True
                
        # 2. Policy -> Items
        policies = db.query(Policy).all()
        for p in policies:
            print(f"Revisando Política: {p.name}")
            if normalize(p.strategic_items): changed = True
                
        # 3. Items -> Activities
        items = db.query(StrategicItem).all()
        for si in items:
            print(f"Revisando Plan/Programa: {si.name}")
            if normalize(si.activities): changed = True
                
        # 4. Activities -> Tasks
        activities = db.query(Activity).all()
        for act in activities:
            print(f"Revisando Actividad: {act.name}")
            if normalize(act.tasks): changed = True
            
        if changed:
            print("\nGuardando cambios...")
            db.commit()
            print("Recalculando todos los porcentajes de avance de la plataforma...")
            CalculationService.recalculate_all(db)
            print("¡Auditoría y corrección finalizada con éxito!")
        else:
            print("\nTodos los pesos jerárquicos están dentro del límite del 100%. No se requirió normalización.")
            
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
