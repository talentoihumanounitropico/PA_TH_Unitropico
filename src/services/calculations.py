from sqlalchemy.orm import Session
from src.models.entities import Task, Activity, StrategicItem, Policy, PlanMacro

class CalculationService:
    """
    Service responsible for propagating progress updates through the 5-level hierarchy.
    Whenever a task is updated, it triggers a recursive recalculation of parent nodes.
    """
    @staticmethod
    def update_all_levels(db: Session, task_id: int):
        """
        Recalculates the entire chain from a single task up to the Plan Macro (5 levels).
        Ensures data consistency across all dashboards.
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task: return

        # 1. Update Activity: Calculate progress based on child tasks
        activity = task.activity
        CalculationService._update_node(db, activity, activity.tasks)

        # 2. Update Strategic Item: Calculate progress based on child activities
        si = activity.strategic_item
        CalculationService._update_node(db, si, si.activities)

        # 3. Update Policy: Calculate progress based on child strategic items
        pol = si.policy
        CalculationService._update_node(db, pol, pol.strategic_items)

        # 4. Update Plan Macro (Gestión TH)
        macro = pol.plan_macro
        CalculationService._update_node(db, macro, macro.policies)

        db.commit()
        db.refresh(macro)

    @staticmethod
    def recalculate_all(db: Session):
        """
        Recalculates progress for all hierarchical levels.
        Useful when weights change at higher levels (e.g. Policies or Programs).
        """
        activities = db.query(Activity).all()
        for act in activities:
            CalculationService._update_node(db, act, act.tasks)
            
        items = db.query(StrategicItem).all()
        for si in items:
            CalculationService._update_node(db, si, si.activities)
            
        policies = db.query(Policy).all()
        for pol in policies:
            CalculationService._update_node(db, pol, pol.strategic_items)
            
        macros = db.query(PlanMacro).all()
        for macro in macros:
            CalculationService._update_node(db, macro, macro.policies)
            
        db.commit()

    @staticmethod
    def _update_node(db: Session, node, children):
        if not children:
            node.progress = 0.0
            return
        
        total_weight = sum(c.weight for c in children)
        if total_weight > 0:
            node.progress = sum(c.progress * (c.weight / total_weight) for c in children)
        else:
            node.progress = sum(c.progress for c in children) / len(children)
        
        db.add(node)

    @staticmethod
    def get_semaforo(progress: float) -> tuple:
        if progress >= 80:
            return "Cumplimiento Sobresaliente", "#10b981"
        elif progress >= 60:
            return "Cumplimiento Aceptable", "#f59e0b"
        else:
            return "Cumplimiento Crítico", "#ef4444"
