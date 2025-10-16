import frappe
from raj_customizations.raj_customizations.overtime_calculation import apply_weekly_overtime
from raj_customizations.raj_customizations.weekly_absence import apply_weekly_deduction

def before_save_salary_slip(doc, method=None):
    #apply_weekly_deduction(doc, method)
    apply_weekly_overtime(doc, method)
