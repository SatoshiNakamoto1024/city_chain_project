#[cfg(test)]
mod tests {
    use super::*;
    use tokio::runtime::Runtime;

    #[test]
    fn test_python_grpc_immudb() {
        let rt = Runtime::new().unwrap();
        rt.block_on(async {
            let addr = "http://127.0.0.1:50051";  // Python gRPC サーバーのアドレス
            let user = "immudb";
            let password = "immudb";

            let mut client = ImmuDBClient::new(addr)
                .await
                .expect("Failed to connect to Python gRPC");

            client.set_value("test_key", "Hello, immuDB!").await.expect("Failed to set value");

            let value = client.get_value("test_key").await.expect("Failed to get value");
            assert_eq!(value, "Hello, immuDB!");
        });
    }
}
