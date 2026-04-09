from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    make_response,
    flash,
)
from config import Config
from models.db import db
from models.user_model import User
from models.claim_model import Claim
from datetime import datetime, timedelta
from sqlalchemy import extract
from utils.helpers import assign_service, detect_priority
from functools import wraps
import qrcode
from io import BytesIO

# PDF classic
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# PDF premium
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "super-secret-key"

db.init_app(app)


# ==============================
# SECURITE AUTHENTIFICATION
# ==============================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Veuillez vous connecter pour accéder au système.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Connexion requise.", "warning")
                return redirect(url_for("login"))

            if session.get("role") != required_role:
                flash("Accès non autorisé.", "danger")
                return redirect(url_for("dashboard"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


# ==============================
# INITIALISATION DB + ADMIN
# ==============================
with app.app_context():
    db.create_all()

    admin = User.query.filter_by(email="admin@coud.sn").first()
    if not admin:
        admin = User(
            full_name="Administrateur COUD",
            email="admin@coud.sn",
            role="admin",
        )
        admin.set_password("Admin@2026")
        db.session.add(admin)
        db.session.commit()


# ==============================
# SIGNATURE SYSTEME
# ==============================
@app.context_processor
def inject_system_signature():
    return {
        "system_signature": "COUD Medical Claims System • Powered by NISME HOME"
    }


# ==============================
# ROUTE ACCUEIL
# ==============================
@app.route("/")
def home():
    return redirect(url_for("login"))


# ==============================
# LOGIN ADMIN + SOUVIENS TOI DE MOI
# ==============================
@app.route("/login", methods=["GET", "POST"])
def login():
    remembered_email = request.cookies.get("remember_email", "")

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        remember_me = request.form.get("remember_me")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["user"] = user.full_name
            session["role"] = user.role

            response = make_response(redirect(url_for("dashboard")))

            if remember_me:
                response.set_cookie(
                    "remember_email",
                    email,
                    max_age=60 * 60 * 24 * 30,
                )
            else:
                response.delete_cookie("remember_email")

            flash("Connexion réussie.", "success")
            return response

        flash("Email ou mot de passe incorrect.", "danger")

    return render_template("login.html", remembered_email=remembered_email)


# ==============================
# LOGOUT
# ==============================
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Déconnexion réussie.", "success")
    return redirect(url_for("login"))


# ==============================
# DASHBOARD ADMIN
# ==============================
@app.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    total = Claim.query.filter_by(is_archived=False).count()
    pending = Claim.query.filter_by(
        status="En attente", is_archived=False
    ).count()
    solved = Claim.query.filter_by(
        status="Résolu", is_archived=True
    ).count()

    claims = (
        Claim.query.filter_by(is_archived=False)
        .order_by(Claim.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "dashboard.html",
        total=total,
        pending=pending,
        solved=solved,
        claims=claims,
    )


# ==============================
# CREATION RECLAMATION INTERNE
# ==============================
@app.route("/claim/new", methods=["GET", "POST"])
@login_required
def create_claim():
    if request.method == "POST":
        subject = request.form["subject"]
        description = request.form["description"]

        claim = Claim(
            ticket_number=f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_name=request.form["patient_name"],
            category=request.form["category"],
            phone=request.form["phone"],
            subject=subject,
            description=description,
            service=assign_service(subject),
            priority=detect_priority(description),
            status="En attente",
            is_archived=False,
            created_at=datetime.utcnow(),
        )

        db.session.add(claim)
        db.session.commit()
        return redirect(url_for("claims_list"))

    return render_template("create_claim.html")


# ==============================
# FORMULAIRE PATIENT QR
# ==============================
@app.route("/patient/form", methods=["GET", "POST"])
def patient_claim_form():
    if request.method == "POST":
        subject = request.form["subject"]
        description = request.form["description"]

        claim = Claim(
            ticket_number=f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            patient_name=request.form["patient_name"],
            category=request.form["category"],
            phone=request.form["phone"],
            subject=subject,
            description=description,
            service=assign_service(subject),
            priority=detect_priority(description),
            status="En attente",
            is_archived=False,
            created_at=datetime.utcnow(),
        )

        db.session.add(claim)
        db.session.commit()

        return render_template(
            "qr_access.html", ticket=claim.ticket_number
        )

    return render_template("patient_claim_form.html")


# ==============================
# LISTE RECLAMATIONS
# ==============================
@app.route("/claims")
@login_required
def claims_list():
    claims = (
        Claim.query.filter_by(is_archived=False)
        .order_by(Claim.created_at.desc())
        .all()
    )
    return render_template("claims_list.html", claims=claims)


# ==============================
# ARCHIVES
# ==============================
@app.route("/claims/archive")
@login_required
def archived_claims():
    claims = (
        Claim.query.filter_by(is_archived=True)
        .order_by(Claim.resolved_at.desc())
        .all()
    )
    return render_template("claims_archive.html", claims=claims)


# ==============================
# RESTAURATION ARCHIVE
# ==============================
@app.route("/claim/<int:id>/restore")
@login_required
def restore_claim(id):
    claim = Claim.query.get_or_404(id)

    claim.status = "En attente"
    claim.is_archived = False
    claim.resolved_at = None

    db.session.commit()

    return redirect(url_for("archived_claims"))

# ==============================
# SUPPRESSION DEFINITIVE ARCHIVE
# ==============================
@app.route("/claim/<int:id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_claim(id):
    claim = Claim.query.get_or_404(id)

    if claim.status != "Résolu" or not claim.is_archived:
        flash(
            "Seules les réclamations résolues et archivées peuvent être supprimées.",
            "danger",
        )
        return redirect(url_for("archived_claims"))

    db.session.delete(claim)
    db.session.commit()

    flash("Réclamation supprimée définitivement avec succès.", "success")
    return redirect(url_for("archived_claims"))

# ==============================
# ESCALATIONS > 24H
# ==============================
@app.route("/admin/escalations")
@login_required
@role_required("admin")
def escalations():
    old_claims = Claim.query.filter_by(
        status="En attente", is_archived=False
    ).all()

    critical = []
    for claim in old_claims:
        delta = datetime.utcnow() - claim.created_at
        if delta.total_seconds() > 86400:
            critical.append(claim)

    return render_template("claims_list.html", claims=critical)


# ==============================
# RESOLUTION + ARCHIVAGE
# ==============================
@app.route("/claim/<int:id>/resolve")
@login_required
def resolve_claim(id):
    claim = Claim.query.get_or_404(id)
    claim.status = "Résolu"
    claim.is_archived = True
    claim.resolved_at = datetime.utcnow()

    db.session.commit()
    return redirect(url_for("claims_list"))


# ==============================
# DASHBOARD REPORTS
# ==============================
@app.route("/admin/reports")
@login_required
@role_required("admin")
def admin_reports():
    total = Claim.query.count()
    pending = Claim.query.filter_by(status="En attente").count()
    solved = Claim.query.filter_by(status="Résolu").count()

    students = Claim.query.filter_by(category="Etudiant").count()
    staff = Claim.query.filter_by(category="Personnel COUD").count()
    external = Claim.query.filter_by(category="Externe").count()

    urgent = Claim.query.filter_by(priority="Urgent").count()

    urgent_claims = (
        Claim.query.filter_by(priority="Urgent")
        .order_by(Claim.created_at.desc())
        .limit(5)
        .all()
    )

    chart_labels = []
    chart_values = []

    for i in range(4, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        start_day = datetime(day.year, day.month, day.day)
        end_day = start_day + timedelta(days=1)

        count = Claim.query.filter(
            Claim.created_at >= start_day,
            Claim.created_at < end_day,
        ).count()

        chart_labels.append(day.strftime("%a"))
        chart_values.append(count)

    selected_month = request.args.get("month", type=int)

    monthly_claims = []
    month_total = 0
    month_solved = 0
    month_urgent = 0

    if selected_month:
        monthly_claims = (
            Claim.query.filter(
                extract("month", Claim.created_at) == selected_month
            )
            .order_by(Claim.created_at.desc())
            .all()
        )

        month_total = len(monthly_claims)
        month_solved = len(
            [c for c in monthly_claims if c.status == "Résolu"]
        )
        month_urgent = len(
            [c for c in monthly_claims if c.priority == "Urgent"]
        )

    return render_template(
        "admin_reports.html",
        total=total,
        pending=pending,
        solved=solved,
        urgent=urgent,
        students=students,
        staff=staff,
        external=external,
        urgent_claims=urgent_claims,
        chart_labels=chart_labels,
        chart_values=chart_values,
        selected_month=selected_month,
        monthly_claims=monthly_claims,
        month_total=month_total,
        month_solved=month_solved,
        month_urgent=month_urgent,
    )


# ==============================
# EXPORT PDF GLOBAL SIMPLE
# ==============================
@app.route("/export_pdf")
@login_required
@role_required("admin")
def export_pdf():
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(100, 800, "Rapport Administrateur - Réclamations")

    total = Claim.query.count()
    pending = Claim.query.filter_by(status="En attente").count()
    solved = Claim.query.filter_by(status="Résolu").count()

    pdf.setFont("Helvetica", 12)
    pdf.drawString(100, 760, f"Total: {total}")
    pdf.drawString(100, 740, f"En attente: {pending}")
    pdf.drawString(100, 720, f"Résolues: {solved}")

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="rapport_admin.pdf",
        mimetype="application/pdf",
    )


# ==============================
# EXPORT PDF PREMIUM DIRECTION V9
# ==============================
@app.route("/admin/export")
@login_required
@role_required("admin")
def export_report():
    claims = Claim.query.order_by(Claim.created_at.desc()).all()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    try:
        story.append(Image("static/assets/logo_coud.png", width=2.5 * cm, height=2.5 * cm))
        story.append(Spacer(1, 0.2 * cm))
    except Exception:
        pass

    try:
        story.append(Image("static/assets/logo_labo.png", width=2.2 * cm, height=2.2 * cm))
        story.append(Spacer(1, 0.3 * cm))
    except Exception:
        pass

    story.append(
        Paragraph(
            "<b>RAPPORT DIRECTION GÉNÉRALE - RÉCLAMATIONS DÉPARTEMENT MÉDICAL</b>",
            styles["Title"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    story.append(
        Paragraph(
            f"<b>Période :</b> {datetime.now().strftime('%d/%m/%Y')} • Rapport mensuel",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    total = len(claims)
    pending = len([c for c in claims if c.status == "En attente"])
    solved = len([c for c in claims if c.status == "Résolu"])

    service_stats = {}
    for c in claims:
        service_stats[c.service] = service_stats.get(c.service, 0) + 1

    top_service = max(service_stats, key=service_stats.get) if service_stats else "N/A"

    story.append(Paragraph(f"<b>Total :</b> {total}", styles["Normal"]))
    story.append(Paragraph(f"<b>En attente :</b> {pending}", styles["Normal"]))
    story.append(Paragraph(f"<b>Résolues :</b> {solved}", styles["Normal"]))
    story.append(
        Paragraph(
            f"<b>Service le plus touché :</b> {top_service}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.6 * cm))

    data = [["Service", "Nombre de réclamations"]]
    for service, count in service_stats.items():
        data.append([service, str(count)])

    stats_table = Table(data, colWidths=[8 * cm, 6 * cm])
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d4ed8")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(stats_table)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("<b>Signature Chef Médical</b>", styles["Normal"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph("_______________________________", styles["Normal"]))

    doc.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="rapport_direction_generale_coud.pdf",
        mimetype="application/pdf",
    )


# ==============================
# EXPORT PDF MENSUEL PREMIUM
# ==============================
@app.route("/export_monthly_pdf")
@login_required
@role_required("admin")
def export_monthly_pdf():
    selected_month = request.args.get("month", type=int)

    claims = []
    if selected_month:
        claims = (
            Claim.query.filter(
                extract("month", Claim.created_at) == selected_month
            )
            .order_by(Claim.created_at.desc())
            .all()
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=50,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    story = []

    try:
        story.append(Image("static/assets/logo_coud.png", width=2.8 * cm, height=2.8 * cm))
    except Exception:
        pass

    story.append(
        Paragraph(
            f"<b>RAPPORT MENSUEL DES RÉCLAMATIONS - MOIS {selected_month}</b>",
            styles["Title"],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    total = len(claims)
    solved = len([c for c in claims if c.status == "Résolu"])
    urgent = len([c for c in claims if c.priority == "Urgent"])

    story.append(Paragraph(f"<b>Total :</b> {total}", styles["Normal"]))
    story.append(Paragraph(f"<b>Résolues :</b> {solved}", styles["Normal"]))
    story.append(Paragraph(f"<b>Urgentes :</b> {urgent}", styles["Normal"]))
    story.append(Spacer(1, 0.6 * cm))

    data = [["Patient", "Service", "Priorité", "Statut", "Date"]]

    for c in claims:
        data.append(
            [
                c.patient_name,
                c.service,
                c.priority,
                c.status,
                c.created_at.strftime("%d/%m/%Y"),
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        Paragraph(
            f"Généré le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')}",
            styles["Italic"],
        )
    )

    doc.build(story)

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"rapport_mensuel_mois_{selected_month}.pdf",
        mimetype="application/pdf",
    )


# ==============================
# GENERATION QR WEB CLIQUABLE
# ==============================
@app.route("/generate_qr")
def generate_qr():
    qr_url = url_for("patient_claim_form", _external=True)

    img = qrcode.make(qr_url)

    buffer = BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


# ==============================
# KEEP ALIVE RENDER / UPTIMEROBOT
# ==============================
@app.route("/ping")
def ping():
    return "COUD Medical Claims System is alive ✅", 200


# ==============================
# LANCEMENT APP
# ==============================
if __name__ == "__main__":
    app.run(debug=True)