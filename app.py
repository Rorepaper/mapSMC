import json
import os
from dataclasses import dataclass

from PIL import Image
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from folium import Map, Element, raster_layers
from branca import utilities

app = Flask(__name__)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///base.db'

db = SQLAlchemy(app)
iframe = ''


@dataclass
class Tree(db.Model):
    id: int = db.Column(db.String(50), primary_key=True)
    parent: str = db.Column(db.String(50), nullable=False)
    text: str = db.Column(db.String(50), nullable=False)
    data: str = db.Column(db.String(300), nullable=False)

    def __repr__(self):
        return "<Tree %r" % self.id


@app.route('/', methods=['POST', "GET"])
def upload_file():
    global iframe
    if request.method == "POST":
        src = ""
        if request.files['file']:
            uploaded_file = request.files['file']
            if uploaded_file.filename != '':
                uploaded_file.save(f"static/plans/{uploaded_file.filename}")
                src = f"static/plans/{uploaded_file.filename}"
                jid = next(request.values.items())[1]
                Tree.query.filter_by(id=jid).one().data = uploaded_file.filename
                db.session.commit()
        else:
            print(request.form)
            d = json.loads(request.form["send_tree"])
            p_name = Tree.query.filter_by(id=d["id"]).one().data
            print(p_name)
            if p_name:
                src = f"static/plans/{p_name}"
        if src:
            im = Image.open(src)
            w, h = im.width, im.height

            white_tile = utilities.image_to_url([[1, 1], [1, 1]])
            m = Map(tiles=white_tile, attr="white tile", zoom_start=4, world_copy_jump=True)

            bounds = ((-90, -(w * 90 / h * 2)), (90, (w * 90 / h * 2)))
            image = raster_layers.ImageOverlay(src, bounds=bounds)

            image.add_to(m)
            m.get_root().width = "600px"
            m.get_root().height = "500px"

            m.get_root().html.add_child(Element(render_template("folium_addon.html", map=m.get_name())))
            iframe = m.get_root()._repr_html_()
            # m.save('templates/map.html')
            print(src)
            return render_template("map.html", iframe=iframe, js=jsonify(Tree.query.all()).json)
        else:
            return render_template("map.html", iframe="", js=jsonify(Tree.query.all()).json)
    else:
        return render_template("map.html", iframe="", js=jsonify(Tree.query.all()).json)


@app.route('/tree', methods=['POST'])
def change_tree():
    global iframe
    # with app.app_context():
    #     db.drop_all()
    #     db.create_all()
    tr = request.json
    table_data = Tree.query.all()
    ad = set([i["id"] for i in tr]).difference(set([i.id for i in table_data]))
    ren = set([i["text"] for i in tr]).difference(set([i.text for i in table_data]))
    de = set([i.id for i in table_data]).difference(set([i["id"] for i in tr]))
    queries = []
    print(ad, de)
    for i in tr:
        if i["id"] in ad:
            queries.append(Tree(id=i["id"], parent=i["parent"], text=i["text"], data=""))
        if i["text"] in ren and i["id"]:
            # TODO: add rename
            ...
        if i["id"] in de:
            obj = Tree.query.filter_by(id=i["id"]).one()
            db.session.delete(obj)
    db.session.add_all(queries)
    db.session.commit()
    return render_template("map.html", iframe=iframe, js=json.dumps(tr))


if __name__ == '__main__':
    app.run(debug=True)
