import json
import os.path

from app import db, TempSet, Creds, app


def init_db():
    app.app_context().push()
    if not os.path.isfile("./instance/temperatures.db"):
        db.create_all()
        print(f"DB CREATED")
    else:
        print("DB ALREADY EXISTS")


def populate_db():
    # init table TempSet
    if not TempSet.query.count() > 0:
        try:
            init_temps = TempSet(temp_set=18, th_set=1, th_outer=5, controller_state="off")
            db.session.add(init_temps)
            db.session.commit()
            print("INIT TEMPS CREATED")
        except Exception as e:
            print(e)
    else:
        print("TEMPS ALREADY EXIST")

    # init table Creds
    if not Creds.query.count() > 0:
        with open('./static/user.json') as f:
            data = json.load(f)
            try:
                user = Creds(user=data['user'], pw=data['pw'])
                db.session.add(user)
                db.session.commit()
                print("INIT CREDS CREATED")
            except Exception as e:
                print(e)
    else:
        print("CREDS ALREADY EXISTS")


if __name__ == "__main__":
    init_db()
    populate_db()
