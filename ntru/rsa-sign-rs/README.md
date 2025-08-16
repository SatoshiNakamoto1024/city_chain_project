結論から言うと、RSAクレート 0.9 系では以前と API が変わっていて、サンプルコードが古いバージョンの書き方のままになっているのが原因です。

特に、

pkcs1v15::PaddingScheme は外部に公開されておらず、代わりに pkcs1v15::Pkcs1v15Encrypt や new_unprefixed() などを使う必要がある
SigningKey::sign() は Result ではなく直接 Signature を返すので .expect(...) は呼べない
VerifyingKey::<Sha256>::new(...) は SHA256 の OID を自動付与しようとしますが、sha2 クレート 0.10.x がそれを満たす AssociatedOid を実装していないため、new_unprefixed() を使う必要がある
…といった点がエラーの主な原因です。


下記に「RSAクレート 0.9.7」対応版のコード例を示します。大きな修正点は、

暗号化/復号化で PaddingScheme::new_pkcs1v15_encrypt() ではなく、pkcs1v15::Pkcs1v15Encrypt を使う
署名時に返ってくるのは Signature 型なので、.expect("Failed to sign message") は不要（= 返り値は失敗をラップした Result ではない）
検証用のキーを VerifyingKey::<Sha256>::new_unprefixed(...) で作る
あわせて、テストコード側で verify_signature(...) と呼んでいるのに実際の関数は verify_message(...) になっているので、そこも名前をそろえる必要があります。

RSA 0.9 系では、以下のようなポイントに注意してコードを修正する必要があります。

PaddingScheme はクレート外部から直接使えない

PaddingScheme::new_pkcs1v15_encrypt() は非公開 (private) になっているため、その代わりに pkcs1v15::Pkcs1v15Encrypt を直接指定する形になります。
signature クレートのトレイトは rsa クレート内に再エクスポートされている

use signature::{Signer, Verifier}; の形では「unresolved import signature」エラーが出ます。
代わりに use rsa::signature::{Signer, Verifier}; として、RSA クレート内の再エクスポートを使う必要があります。
SigningKey::<Sha256>::new_unprefixed(...) と VerifyingKey::<Sha256>::new_unprefixed(...) を使う

new(...) は SHA256 の OID を自動付与しようとして、sha2 0.10 系が AssociatedOid を実装していないためにコンパイルエラーになります。
new_unprefixed(...) なら OID が不要なのでエラーになりません。
sign() が直接 Signature を返すので expect(...) は不要

以前のバージョンの rsa クレートでは .sign(...) が Result<Signature, Error> を返していましたが、0.9 系では Signature を直接返すため .expect(...) は呼べません。
テストコードで verify_signature ではなく verify_message (関数名の不一致に注意)

テストコードのほうで関数名を一致させる必要があります。