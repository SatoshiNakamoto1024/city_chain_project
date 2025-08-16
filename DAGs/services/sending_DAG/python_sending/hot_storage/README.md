    │   ├── hot_storage/                 # MongoDB Hot 保存レイヤ
    │   │   ├── db_handler.py            # CSFLE＋NTRU 包装ラッパ
    │   │   ├── batch_writer.py          # municipality 完了バッチ書込

hot_storage/
City レイヤの「完了バッチ」を MongoDB Hot コレクションに高速書込。