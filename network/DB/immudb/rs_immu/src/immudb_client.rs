use crate::immudb::{
    immu_service_client::ImmuServiceClient,
    // ScanResponse,  <-- 使ってないなら削除
    LoginRequest, LoginResponse,
    LogoutRequest, LogoutResponse,
    SetRequest, SetResponse,
    GetRequest, GetResponse,
    MultiSetRequest, MultiSetResponse,
    ScanRequest,            // これは使ってる
    DeleteRequest, DeleteResponse,
};

use tonic::{transport::Channel, Request};
use std::error::Error;

/// Rust 用クライアント構造体（Python の gRPC サーバーに接続する）
#[derive(Clone)]  // ★ これで ImmuDBClient が Clone 可能になる
pub struct ImmuDBClient {
    inner: ImmuServiceClient<Channel>,
}

impl ImmuDBClient {
    /// gRPC サーバーに接続（Python側で起動中）
    pub async fn new(addr: &str) -> Result<Self, Box<dyn Error>> {
        // すでに "http://" などが含まれているならそのまま使う
        let uri = if addr.starts_with("http://") || addr.starts_with("https://") {
            addr.to_string()
        } else {
            format!("http://{}", addr)
        };
        let channel = Channel::from_shared(uri)?
            .connect()
            .await?;
        Ok(Self {
            inner: ImmuServiceClient::new(channel),
        })
    }

    /// Login
    pub async fn login(&mut self, user: &str, pass: &str, continent: &str) -> Result<String, Box<dyn Error>> {
        let req = LoginRequest {
            user: user.to_string(),
            password: pass.to_string(),
            continent: continent.to_string(),
        };
        let resp = self.inner.login(Request::new(req)).await?;
        let data: LoginResponse = resp.into_inner();
        Ok(data.token)
    }

    /// Logout
    pub async fn logout(&mut self, token: &str) -> Result<LogoutResponse, Box<dyn Error>> {
        let req = LogoutRequest {
            token: token.to_string(),
        };
        let resp = self.inner.logout(Request::new(req)).await?;
        Ok(resp.into_inner())
    }

    /// Set (value を &[u8] で受け取る)
    pub async fn set_value(&mut self, token: &str, key: &str, val: &[u8]) -> Result<SetResponse, Box<dyn Error>> {
        let req = SetRequest {
            token: token.to_string(),
            key: key.to_string(),
            value: val.to_vec(),
        };
    
        match self.inner.set(Request::new(req)).await {
            Ok(resp) => {
                let res = resp.into_inner();
                println!(
                    "[Rust] Set Success: key={} value={:?}",
                    key,
                    val
                );
                Ok(res)
            }
            Err(e) => {
                eprintln!("[Rust] Set Error: {}", e);
                Err(Box::new(e))
            }
        }
    }

    /// Get
    pub async fn get_value(&mut self, token: &str, key: &str) -> Result<GetResponse, Box<dyn Error>> {
        let req = GetRequest {
            token: token.to_string(),
            key: key.to_string(),
        };
    
        match self.inner.get(Request::new(req)).await {
            Ok(resp) => {
                let mut res = resp.into_inner();
                let decoded_value = String::from_utf8(res.value.clone())
                    .unwrap_or_else(|_| "<invalid utf-8>".to_string());
                println!(
                    "[Rust] Get Success: key={} value={}",
                    key,
                    decoded_value
                );
                // ここでレスポンスの value を上書きしているので
                // 最終的に呼び出し元に返る value は "UTF-8文字列化されたbytes"
                // 必要ならこのままでもOK。あるいはバイトのまま残すなら不要。
                res.value = decoded_value.into_bytes();
                Ok(res)
            }
            Err(e) => {
                eprintln!("[Rust] Get Error: {}", e);
                Err(Box::new(e))
            }
        }
    }

    /// MultiSet
    pub async fn multi_set(&mut self, token: &str, kvs: Vec<(String, String)>)
        -> Result<MultiSetResponse, Box<dyn Error>>
    {
        let kv_list = kvs.into_iter().map(|(k, v)| {
            crate::immudb::KeyValue {
                key: k.into_bytes(),
                value: v.into_bytes(),
            }
        }).collect();

        let req = MultiSetRequest {
            token: token.to_string(),
            kvs: kv_list,
        };

        let resp = self.inner.multi_set(Request::new(req)).await?;
        Ok(resp.into_inner())
    }

    /// Scan
    pub async fn scan(&mut self, token: &str, prefix: &str, desc: bool, limit: u32)
        -> Result<Vec<(String, String)>, Box<dyn Error>>
    {
        let req = ScanRequest {
            token: token.to_string(),
            prefix: prefix.to_string(),
            desc,
            limit,
        };

        let resp = self.inner.scan(Request::new(req)).await?;
        let scan_response = resp.into_inner();

        let items: Vec<(String, String)> = scan_response.items
            .into_iter()
            .map(|kv| {
                let k = String::from_utf8(kv.key).unwrap_or_default();
                let v = String::from_utf8(kv.value).unwrap_or_default();
                (k, v)
            })
            .collect();

        Ok(items)
    }

    /// Delete
    pub async fn delete(&mut self, token: &str, key: &str) -> Result<DeleteResponse, Box<dyn Error>> {
        let req = DeleteRequest {
            token: token.to_string(),
            key: key.to_string(),
        };
        let resp = self.inner.delete(Request::new(req)).await?;
        Ok(resp.into_inner())
    }
}
