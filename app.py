from flask import (
    Flask, render_template, request, redirect, url_for,flash, session, send_file, jsonify
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from fpdf import FPDF
import datetime

# ---- App setup ----
app = Flask(__name__)
app.secret_key = "change_this_in_production"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'  # delete file to recreate fresh schema
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# helper to show current year in templates
@app.context_processor
def inject_now():
    return {'now_year': datetime.datetime.utcnow().year}

# ---- Models ----
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    prakriti = db.Column(db.String(100))      # Vata/Pitta/Kapha/combination/Balanced
    agni = db.Column(db.String(50))           # weak/normal/hyper
    ama = db.Column(db.String(50))            # present/absent/mild
    allergy = db.Column(db.String(250))       # comma-separated
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    meals = db.relationship('MealLog', backref='patient', lazy=True)

class MealLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.date.today)
    meal = db.Column(db.String(250), nullable=False)
    meal_type = db.Column(db.String(50), nullable=True)  # Breakfast/Lunch/Dinner/Snack
    eaten = db.Column(db.Boolean, default=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)

# Create tables
with app.app_context():
    db.create_all()

# ---- Nutrition DB (simplified) ----
# (You can expand to many more items or move to a separate JSON / DB table)
# ---- Nutrition DB (30+ items) ----
nutrition_db = {
    "Idli": {"calories": 58, "protein": 2, "carbs": 12, "fat": 0.2},
    "Dosa": {"calories": 133, "protein": 3, "carbs": 19, "fat": 4},
    "Khichdi": {"calories": 280, "protein": 10, "carbs": 45, "fat": 4},
    "Rice with dal": {"calories": 350, "protein": 10, "carbs": 60, "fat": 4},
    "Chapati": {"calories": 120, "protein": 4, "carbs": 20, "fat": 1},
    "Paratha": {"calories": 200, "protein": 5, "carbs": 30, "fat": 8},
    "Upma": {"calories": 140, "protein": 4, "carbs": 25, "fat": 3},
    "Poha": {"calories": 130, "protein": 3, "carbs": 23, "fat": 2},
    "Pongal": {"calories": 220, "protein": 7, "carbs": 40, "fat": 5},
    "Sambar": {"calories": 90, "protein": 3, "carbs": 15, "fat": 2},
    "Rasam": {"calories": 30, "protein": 1, "carbs": 5, "fat": 0.1},
    "Vegetable curry": {"calories": 150, "protein": 4, "carbs": 12, "fat": 7},
    "Paneer curry": {"calories": 320, "protein": 14, "carbs": 8, "fat": 22},
    "Cucumber salad": {"calories": 16, "protein": 0.7, "carbs": 3.6, "fat": 0.1},
    "Curd rice": {"calories": 320, "protein": 9, "carbs": 55, "fat": 6},
    "Moong dal khichdi": {"calories": 220, "protein": 10, "carbs": 36, "fat": 2},
    "Grilled fish": {"calories": 200, "protein": 22, "carbs": 0, "fat": 12},
    "Chicken curry": {"calories": 350, "protein": 25, "carbs": 6, "fat": 22},
    "Pumpkin soup": {"calories": 90, "protein": 2, "carbs": 15, "fat": 1},
    "Ginger tea": {"calories": 10, "protein": 0, "carbs": 2, "fat": 0},
    "Coconut water": {"calories": 19, "protein": 0.7, "carbs": 3.7, "fat": 0.2},
    "Buttermilk": {"calories": 40, "protein": 3, "carbs": 4, "fat": 1},
    "Quinoa salad": {"calories": 120, "protein": 4, "carbs": 21, "fat": 2},
    "Boiled eggs": {"calories": 155, "protein": 13, "carbs": 1, "fat": 11},
    "Masala omelette": {"calories": 180, "protein": 12, "carbs": 3, "fat": 14},
    "Chana masala": {"calories": 250, "protein": 12, "carbs": 35, "fat": 6},
    "Tofu stir fry": {"calories": 200, "protein": 15, "carbs": 10, "fat": 12},
    "Steamed vegetables": {"calories": 50, "protein": 2, "carbs": 10, "fat": 0.5},
    "Fruit salad": {"calories": 90, "protein": 1, "carbs": 22, "fat": 0.2},
    "Smoothie": {"calories": 150, "protein": 3, "carbs": 30, "fat": 2},
}


# Meal groups
# ---- Breakfast, Lunch, Dinner Lists (30+ items) ----

breakfast_list = [
    "Idli", "Dosa", "Upma", "Poha", "Pongal",
    "Oats porridge", "Masala omelette", "Boiled eggs",
    "Fruit salad", "Smoothie", "Chia pudding", "Paratha",
    "Nut butter toast", "Vegetable sandwich", "Methi thepla"
]

lunch_list = [
    "Khichdi", "Rice with dal", "Chapati", "Paratha",
    "Sambar", "Vegetable curry", "Paneer curry",
    "Moong dal khichdi", "Chana masala", "Quinoa salad",
    "Grilled chicken", "Grilled fish", "Tofu stir fry",
    "Rajma curry", "Mixed vegetable pulao"
]

dinner_list = [
    "Pumpkin soup", "Vegetable soup", "Steamed vegetables",
    "Cucumber salad", "Curd rice", "Buttermilk",
    "Ginger tea", "Coconut water", "Light dal curry",
    "Stir-fried tofu", "Steamed fish", "Spinach soup",
    "Broccoli stir fry", "Vegetable khichdi", "Tomato soup"
]

def generate_meal_plan(prakriti, agni, ama):
    plan = {"Breakfast": [], "Lunch": [], "Dinner": []}

    if not prakriti or prakriti.lower() == "balanced":
        plan["Breakfast"] = breakfast_list[:5]
        plan["Lunch"] = lunch_list[:5]
        plan["Dinner"] = dinner_list[:5]
    elif "vata" in prakriti.lower():
        plan["Breakfast"] = ["Oats porridge","Idli","Poha","Upma","Fruit salad"]
        plan["Lunch"] = ["Khichdi","Rice with dal","Moong dal khichdi","Vegetable curry","Paneer curry"]
        plan["Dinner"] = ["Moong dal khichdi","Vegetable soup","Curd rice","Pumpkin soup","Steamed vegetables"]
    elif "pitta" in prakriti.lower():
        plan["Breakfast"] = ["Smoothie","Chia pudding","Fruit salad","Boiled eggs","Nut butter toast"]
        plan["Lunch"] = ["Curd rice","Cucumber salad","Rice with dal","Grilled fish","Tofu stir fry"]
        plan["Dinner"] = ["Pumpkin soup","Light dal curry","Steamed fish","Vegetable khichdi","Broccoli stir fry"]
    elif "kapha" in prakriti.lower():
        plan["Breakfast"] = ["Upma","Masala omelette","Poha","Vegetable sandwich","Methi thepla"]
        plan["Lunch"] = ["Chana masala","Grilled chicken","Rajma curry","Mixed vegetable pulao","Quinoa salad"]
        plan["Dinner"] = ["Light dal curry","Spinach soup","Broccoli stir fry","Steamed vegetables","Tomato soup"]
    else:
        plan["Breakfast"] = breakfast_list[:5]
        plan["Lunch"] = lunch_list[:5]
        plan["Dinner"] = dinner_list[:5]

    if agni=="weak" or ama=="present":
        for meal in plan:
            for i, item in enumerate(plan[meal]):
                if "Khichdi" in item or "soup" in item.lower():
                    plan[meal][i] = item

    return plan


# ---- Analysis helpers: prakriti, agni, ama, diet rules ----
def analyze_prakriti_and_agni_ama(features):
    """
    features: dict with keys like 'sleep','skin','digestion','appetite','body_build','temp_sensitivity','mood','agni','ama_signs'
    Returns: (prakriti_string, agni, ama)
    """
    scores = {"Vata": 0, "Pitta": 0, "Kapha": 0}
    mapping = {
        "sleep": {"light": "Vata", "disturbed": "Vata", "deep": "Kapha", "balanced": "Pitta"},
        "skin": {"dry": "Vata", "oily": "Pitta", "moist": "Kapha", "normal": "Pitta"},
        "digestion": {"irregular": "Vata", "strong": "Pitta", "slow": "Kapha", "normal": "Pitta"},
        "appetite": {"variable": "Vata", "strong": "Pitta", "low": "Kapha"},
        "body_build": {"thin": "Vata", "medium": "Pitta", "heavy": "Kapha"},
        "temp_sensitivity": {"cold": "Vata", "hot": "Pitta", "cool": "Kapha"},
        "mood": {"anxious": "Vata", "irritable": "Pitta", "calm": "Kapha"}
    }
    for k, v in features.items():
        if not v: continue
        val = v.strip().lower()
        if k in mapping:
            pick = mapping[k].get(val)
            if pick:
                scores[pick] += 1

    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top = [k for k,v in sorted_scores if v == sorted_scores[0][1] and v>0]
    if len(top)==0:
        prakriti = "Balanced"
    elif len(top)==1:
        prakriti = top[0]
    else:
        prakriti = "-".join(top)

    # Agni: use provided 'agni' in features or infer from digestion/appetite
    agni = features.get("agni")
    if not agni:
        digestion = features.get("digestion","").strip().lower()
        appetite = features.get("appetite","").strip().lower()
        if digestion == "weak" or appetite == "low" or digestion=="slow":
            agni = "weak"
        elif digestion == "strong":
            agni = "strong"
        else:
            agni = "normal"

    # Ama: signs from features['ama_signs'] (string like bloating, heaviness)
    ama_signs = features.get("ama_signs","").strip().lower()
    if ama_signs:
        ama = "present"
    else:
        ama = "absent"

    return prakriti, agni, ama

def evaluate_food(food_name, prakriti, agni, ama, allergy_list=None):
    """
    Return (ok_boolean, message). Uses simple keyword matching to propose suitability.
    """
    # allergy check
    if allergy_list:
        for a in allergy_list:
            if a.strip() and a.strip().lower() in food_name.lower():
                return False, f"Contains allergen '{a.strip()}'. Avoid."

    name = food_name.lower()
    # Basic rules (very simple, meant to be refined)
    if prakriti and "vata" in prakriti.lower():
        if any(x in name for x in ["oats","khichdi","porridge","warm","ghee","rice","dal","soups"]):
            return True, "Good for Vata: warm, grounding foods."
        if any(x in name for x in ["fried","cold","raw","salad"]):
            return False, "Avoid raw/cold/fried foods for Vata."

    if prakriti and "pitta" in prakriti.lower():
        if any(x in name for x in ["curd","cucumber","coconut","rice","cool","sweet","buttermilk"]):
            return True, "Cooling for Pitta."
        if any(x in name for x in ["spicy","hot","fried","chili","ginger"]):
            return False, "May aggravate Pitta (hot/spicy)."

    if prakriti and "kapha" in prakriti.lower():
        if any(x in name for x in ["grilled","spicy","light","barley","lentils","salad","ginger"]):
            return True, "Light/spicy is good for Kapha."
        if any(x in name for x in ["dairy","oily","heavy","sweet","butter","paneer"]):
            return False, "Avoid heavy/dairy/sweet for Kapha."

    # agni/ama adjustments
    if agni == "weak":
        # prefer light, easy-to-digest: khichdi, soups
        if any(x in name for x in ["khichdi","moong","soup","steamed","rice"]):
            return True, "Good for weak Agni (easy to digest)."
        else:
            return False, "Prefer easy-to-digest foods for weak Agni."

    if ama == "present":
        if any(x in name for x in ["ginger","warm","steamed","khichdi","light","cooked"]):
            return True, "Good to help clear Ama."
        else:
            return False, "Avoid heavy foods until Ama reduces."

    # default neutral
    return True, "No major contraindication found."

def generate_meal_plan(prakriti, agni, ama):
    """Return a dictionary with Breakfast/Lunch/Dinner lists (3-5 items each)."""
    plan = {"Breakfast": [], "Lunch": [], "Dinner": []}
    if not prakriti or prakriti.lower()=="balanced":
        plan["Breakfast"] = breakfast_list[:3]
        plan["Lunch"] = lunch_list[:4]
        plan["Dinner"] = dinner_list[:3]
    elif "vata" in prakriti.lower():
        plan["Breakfast"] = ["Oats porridge","Idli","Poha"]
        plan["Lunch"] = ["Khichdi","Rice with dal","Steamed vegetables with rice"]
        plan["Dinner"] = ["Moong dal khichdi","Vegetable soup","Curd rice"]
    elif "pitta" in prakriti.lower():
        plan["Breakfast"] = ["Fruit salad","Chia pudding","Smoothie"]  # if present
        plan["Lunch"] = ["Curd rice","Cucumber salad","Rice with dal"]
        plan["Dinner"] = ["Pumpkin soup","Light vegetable curry","Curd with rice"]
    elif "kapha" in prakriti.lower():
        plan["Breakfast"] = ["Upma","Masala omelette","Poha"]
        plan["Lunch"] = ["Chana masala","Grilled fish","Tofu stir fry"] if "Grilled fish" in nutrition_db else ["Chana masala","Khichdi"]
        plan["Dinner"] = ["Light vegetable curry","Cabbage stir fry","Pumpkin soup"]
    else:
        # combined types: take a mix
        plan["Breakfast"] = breakfast_list[:3]
        plan["Lunch"] = lunch_list[:4]
        plan["Dinner"] = dinner_list[:3]

    # remove items not present in nutrition_db
    for k in plan:
        plan[k] = [it for it in plan[k] if it in nutrition_db]
        # if agni weak or ama present, prefer soups/khichdi
        if agni=="weak" or ama=="present":
            # make sure khichdi/soup present
            if "Khichdi" in nutrition_db and "Khichdi" not in plan[k] and len(plan[k])>0:
                plan[k][0] = "Khichdi"
    return plan

def nutrition_summary(selected_items):
    total = {"calories":0, "protein":0, "carbs":0, "fat":0}
    details = {}
    for i in selected_items:
        info = nutrition_db.get(i)
        if info:
            details[i] = info
            total["calories"] += info.get("calories",0)
            total["protein"] += info.get("protein",0)
            total["carbs"] += info.get("carbs",0)
            total["fat"] += info.get("fat",0)
    # round
    for k in total:
        total[k] = round(total[k], 1)
    return total, details

def seasonal_recommendations():
    m = datetime.date.today().month
    if m in [12,1,2]:
        return ["Ginger tea","Warm soups","Khichdi"]
    if m in [3,4,5]:
        return ["Coconut water","Cucumber salad","Light fruits"]
    if m in [6,7,8,9]:
        return ["Light soups","Steamed veggies","Ginger"]
    return ["Barley","Warm grains","Ghee in moderation"]

# ---- Routes ----
@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Registration
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=="POST":
        name = request.form.get('name')
        age = request.form.get('age')
        email = request.form.get('email')
        password = request.form.get('password')
        allergy = request.form.get('allergy')
        if not name or not email or not password:
            flash("Name, email and password are required", "danger")
            return redirect(url_for('register'))
        if Patient.query.filter_by(email=email).first():
            flash("Email already registered", "danger")
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        p = Patient(name=name, age=int(age) if age else None, email=email, password=hashed, allergy=allergy)
        db.session.add(p)
        db.session.commit()
        flash("Registration successful — please login", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=="POST":
        email = request.form.get('email')
        password = request.form.get('password')
        p = Patient.query.filter_by(email=email).first()
        if not p or not check_password_hash(p.password, password):
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))
        session['user_id'] = p.id
        flash("Welcome back!", "success")
        return redirect(url_for('dashboard'))
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Logged out", "info")
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    today = datetime.date.today()
    meals_today = MealLog.query.filter_by(patient_id=p.id, date=today).all()
    seasonal = seasonal_recommendations()
    return render_template('dashboard.html', patient=p, meals=meals_today, seasonal=seasonal)

# Questionnaire (prakriti + agni + ama signs)
@app.route('/questionnaire', methods=['GET','POST'])
def questionnaire():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    if request.method=="POST":
        features = {
            "sleep": request.form.get('sleep'),
            "skin": request.form.get('skin'),
            "digestion": request.form.get('digestion'),
            "appetite": request.form.get('appetite'),
            "body_build": request.form.get('body_build'),
            "temp_sensitivity": request.form.get('temp_sensitivity'),
            "mood": request.form.get('mood'),
            "agni": request.form.get('agni'),            # user-entered agni
            "ama_signs": request.form.get('ama_signs')   # free text of ama signs
        }
        prakriti, agni, ama = analyze_prakriti_and_agni_ama(features)
        p.prakriti = prakriti
        p.agni = agni
        p.ama = ama
        db.session.commit()
        flash(f"Analysis complete: Prakriti={prakriti}, Agni={agni}, Ama={ama}", "success")
        return redirect(url_for('diet_plan_page'))
    return render_template('questionnaire.html', patient=p)

# Diet plan display (view last generated or generate from stored)
@app.route('/diet_plan_page')
def diet_plan_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    if not p.prakriti:
        flash("Fill the questionnaire first to get a tailored plan", "warning")
        return redirect(url_for('questionnaire'))
    plan = generate_meal_plan(p.prakriti, p.agni, p.ama)
    selected = [i for sub in plan.values() for i in sub]
    total, details = nutrition_summary(selected)
    allergy_list = [a.strip() for a in (p.allergy or "").split(",") if a.strip()]
    evaluation = {item: evaluate_food(item, p.prakriti, p.agni, p.ama, allergy_list) for item in selected}
    # Convert each eval tuple to dict
    evaluation = {k: {"ok": v[0], "msg": v[1]} for k,v in evaluation.items()}
    nutrition = {"total": total, "details": details}
    return render_template('diet_plan_page.html', patient=p, plan=plan, nutrition=nutrition, evaluation=evaluation)

# Add a meal (log)
@app.route('/log_meal', methods=['POST'])
def log_meal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    meal_name = request.form.get('meal_name')
    meal_type = request.form.get('meal_type') or "Snack"
    if meal_name:
        new = MealLog(meal=meal_name.strip(), meal_type=meal_type, patient_id=session['user_id'])
        db.session.add(new)
        db.session.commit()
        flash(f"Saved meal: {meal_name}", "success")
    return redirect(url_for('dashboard'))

# Mark eaten toggles from meal_log page
@app.route('/update_meal_log', methods=['POST'])
def update_meal_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Expect form keys like eaten_<id>
    for key in request.form:
        if key.startswith('eaten_'):
            mid = key.split('_',1)[1]
            m = MealLog.query.get(int(mid))
            if m and m.patient_id==session['user_id']:
                m.eaten = True
    db.session.commit()
    flash("Meal log updated", "success")
    return redirect(url_for('meal_log'))

# Show meal log
@app.route('/meal_log')
def meal_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    # show last 7 days
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=7)
    meals = MealLog.query.filter(MealLog.patient_id==p.id, MealLog.date>=from_date).order_by(MealLog.date.desc()).all()
    return render_template('meal_log.html', patient=p, meals=meals)

# Nutrition analysis page for today's meals
@app.route('/nutrition_analysis')
def nutrition_analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    today = datetime.date.today()
    meals = MealLog.query.filter_by(patient_id=p.id, date=today).all()
    items = [m.meal for m in meals]
    total, details = nutrition_summary(items)
    return render_template('nutrition_analysis.html', patient=p, items=items, total=total, details=details)

@app.route('/export_diet')
def export_diet():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    p = Patient.query.get(session['user_id'])
    today = datetime.date.today()
    meals = MealLog.query.filter_by(patient_id=p.id, date=today).all()

    if not meals:
        flash("No meals logged for today!", "warning")
        return redirect(url_for('diet_plan_page'))  # fixed redirect

    # Group meals by type
    meal_sections = {"Breakfast": [], "Lunch": [], "Dinner": []}
    for m in meals:
        if m.meal_type in meal_sections:
            meal_sections[m.meal_type].append(m)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"{p.name} - Diet Plan ({today.isoformat()})", ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("Arial", "B", 14)

    # Loop through meals
    for section, items in meal_sections.items():
        if items:
            pdf.set_fill_color(200, 230, 201)  # Light green header
            pdf.cell(0, 10, section, ln=True, fill=True)
            pdf.ln(2)
            pdf.set_font("Arial", "", 12)
            for m in items:
                safe_meal = f"- {m.meal}"
                safe_meal = safe_meal.replace("—", "-").replace("–", "-").replace("•", "-")
                pdf.multi_cell(0, 7, safe_meal)
            pdf.ln(3)
            pdf.set_font("Arial", "B", 14)

    # Nutrition summary table
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Nutrition Summary", ln=True)
    pdf.ln(2)

    pdf.set_font("Arial", "B", 12)
    col_widths = [70, 30, 30, 30, 30]
    headers = ["Item", "Calories", "Protein", "Carbs", "Fat"]

    # Table header
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1, align="C")
    pdf.ln()

    pdf.set_font("Arial", "", 12)
    total_calories = total_protein = total_carbs = total_fat = 0

    for m in meals:
        meal_name = (m.meal[:50] + "...") if len(m.meal) > 50 else m.meal
        info = nutrition_db.get(m.meal, {"calories":0,"protein":0,"carbs":0,"fat":0})

        pdf.cell(col_widths[0], 8, meal_name, border=1)
        pdf.cell(col_widths[1], 8, str(info["calories"]), border=1, align="C")
        pdf.cell(col_widths[2], 8, str(info["protein"]), border=1, align="C")
        pdf.cell(col_widths[3], 8, str(info["carbs"]), border=1, align="C")
        pdf.cell(col_widths[4], 8, str(info["fat"]), border=1, align="C")
        pdf.ln()

        total_calories += info["calories"]
        total_protein += info["protein"]
        total_carbs += info["carbs"]
        total_fat += info["fat"]

    # Total row
    pdf.set_font("Arial", "B", 12)
    pdf.cell(col_widths[0], 8, "Total", border=1, align="C")
    pdf.cell(col_widths[1], 8, str(total_calories), border=1, align="C")
    pdf.cell(col_widths[2], 8, str(total_protein), border=1, align="C")
    pdf.cell(col_widths[3], 8, str(total_carbs), border=1, align="C")
    pdf.cell(col_widths[4], 8, str(total_fat), border=1, align="C")
    pdf.ln()

    # Send PDF
    out = BytesIO()
    pdf.output(out)
    out.seek(0)

    return send_file(
        out,
        download_name=f"diet_{today.isoformat()}.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )
# User profile
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    p = Patient.query.get(session['user_id'])
    return render_template('profile.html', patient=p)

# Simple placeholder endpoint for ML suggestions (future)
@app.route('/api/ml/suggest', methods=['POST'])
def ml_suggest():
    # This is a placeholder. In production you'd load a trained model and return predictions.
    data = request.get_json() or {}
    # Example: accept {"user_id": 1, "history": [...]}
    suggestions = {
        "message": "ML service placeholder — train a model on user logs and return personalized items.",
        "recommended_items": ["Khichdi", "Cucumber salad", "Ginger tea"]
    }
    return jsonify(suggestions)

# ---- Run ----
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
