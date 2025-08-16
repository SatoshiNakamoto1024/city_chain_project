1. admin_tools/register_admin.py
＞ 注意

このファイルは「開発管理者用(admin)」として残しておきますが、
承認フロー（municipality_verification）では「市町村職員(staff)」を使います。
テストでもこちらは使わず、「municipality_registration/service.py」の register_municipality を呼ぶ想定です。