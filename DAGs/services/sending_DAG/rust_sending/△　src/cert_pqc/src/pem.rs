//sending_DAG/rust_sending/cert_pqc/src/pem.rs
//! PEM パーサ（超簡易：鍵本体を HEX で返す）
use regex::Regex;
use once_cell::sync::Lazy;

static PRIV_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"-----BEGIN (.+) PRIVATE KEY-----(?s)(.+?)-----END").unwrap());
static PUB_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"-----BEGIN (.+) PUBLIC KEY-----(?s)(.+?)-----END").unwrap());

pub fn extract_priv_hex(pem: &str) -> Option<String> {
    PRIV_RE
        .captures(pem)
        .and_then(|cap| Some(b64_to_hex(&cap[2])))
}
pub fn extract_pub_hex(pem: &str) -> Option<String> {
    PUB_RE
        .captures(pem)
        .and_then(|cap| Some(b64_to_hex(&cap[2])))
}

fn b64_to_hex(b64_body: &str) -> String {
    let bytes = base64::decode(b64_body.replace('\n', "").trim()).unwrap();
    hex::encode(bytes)
}
