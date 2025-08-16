//sending_DAG/rust_sending/cert_pqc/src/main_cert.rs
use cert_rust::signer::dilithium_sign_stub;
use cert_rust::verifier::dilithium_verify_stub;

fn main() {
    let msg = "hello-cert";
    let sig = dilithium_sign_stub(msg.into(), "dead".into());
    println!("verify = {}", dilithium_verify_stub(msg.into(), sig, "beef".into()));
}
