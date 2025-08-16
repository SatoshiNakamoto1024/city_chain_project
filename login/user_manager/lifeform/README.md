├── lifeform/
    ├── app_lifeform.py
    ├── lifeform.py    　 　# 生命体管理
    ├── lifeform_check.py   # 生命体正誤性チェック
    ├── lifeform_data/
        ├── lifeform.....json    # 予備でローカル管理

ポイント:
create_app() で Flask インスタンスを作り lifeform_bp を /lifeform のprefixで登録。
GET /lifeform → templates/lifeform.html を返す
POST /lifeform → フォームまたは JSON からのデータを user_manager.user_service.register_lifeform で登録
モジュール単体起動 (python app_lifeform.py) でローカルサーバーが localhost:5000 で起動