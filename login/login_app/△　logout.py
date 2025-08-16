from flask import Blueprint, render_template

logout_bp = Blueprint("logout", __name__, template_folder="templates")

@logout_bp.route("/", methods=["GET"])
def logout():
    # 実際には localStorage で JWT を管理しているので、ここではテンプレート表示だけ
    return render_template("logout.html")
