use crate::immudb::{
    immu_service_client::ImmuServiceClient,  // Tonic が自動生成したクライアント
    LoginRequest, LoginResponse,
    LogoutRequest, LogoutResponse,
    SetRequest, SetResponse,
    GetRequest, GetResponse,
    MultiSetRequest, MultiSetResponse,
    ScanRequest, ScanResponse,
    DeleteRequest, DeleteResponse,
};

use tonic::{transport::Channel, Request};
use std::error::Error;

/// Rust 用クライアント構造体 (Pythonの gRPCサーバーを呼ぶ)
pub struct ImmuDBClient {
    inner: ImmuServiceClient<Channel>,
}

impl ImmuDBClient {
    /// gRPCサーバーに接続 (Python側で起動中)
    pub async fn new(addr: &str) -> Result<Self, Box<dyn Error>> {
        let channel = Channel::from_shared(addr.to_string())?
            .connect()
            .await?;
        Ok(Self {
            inner: ImmuServiceClient::new(channel),
        })
    }

    /// Login
    pub async fn login(&mut self, user: &str, pass: &str) -> Result<String, Box<dyn Error>> {
        let req = LoginRequest {
            user: user.to_string(),
            password: pass.to_string(),
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

    /// Set
    pub async fn set_value(&mut self, key: &str, val: &str) -> Result<SetResponse, Box<dyn Error>> {
        let req = SetRequest {
            key: key.to_string(),
            value: val.to_string(),
        };

        match self.inner.set(Request::new(req)).await {
            Ok(resp) => {
                let res = resp.into_inner();
                if res.success {
                    println!("[Rust] Set Success: key={} value={}", key, val);
                } else {
                    eprintln!("[Rust] Set Failed: {}", res.message);
                }
                Ok(res)
            }
            Err(e) => {
                eprintln!("[Rust] Set Error: {}", e);
                Err(Box::new(e))
            }
        }
    }

    /// Get
    pub async fn get_value(&mut self, key: &str) -> Result<GetResponse, Box<dyn Error>> {
        let req = GetRequest {
            key: key.to_string(),
        };

        match self.inner.get(Request::new(req)).await {
            Ok(resp) => {
                let res = resp.into_inner();
                if res.success {
                    println!("[Rust] Get Success: key={} value={}", key, res.value);
                } else {
                    eprintln!("[Rust] Get Failed: {}", res.value);
                }
                Ok(res)
            }
            Err(e) => {
                eprintln!("[Rust] Get Error: {}", e);
                Err(Box::new(e))
            }
        }
    }

    pub async fn multi_set(&mut self, token: &str, kvs: Vec<(String, String)>)
        -> Result<MultiSetResponse, Box<dyn Error>>
    {
        let kv_list = kvs.into_iter().map(|(k, v)| crate::immudb::KeyValue {
            key: k.into_bytes(),
            value: v.into_bytes(),
        }).collect();

        let req = MultiSetRequest {
            token: token.to_string(),
            kvs: kv_list,
        };

        let resp = self.inner.multi_set(Request::new(req)).await?;
        Ok(resp.into_inner())
    }

    pub async fn scan(&mut self, token: &str, prefix: &str, limit: u32)
        -> Result<Vec<(String, String)>, Box<dyn Error>>
    {
        let req = ScanRequest {
            token: token.to_string(),
            prefix: prefix.to_string(),
            limit,
        };

        let resp = self.inner.scan(Request::new(req)).await?;
        let scan_response = resp.into_inner();

        let items: Vec<(String, String)> = scan_response.items
            .into_iter()
            .map(|kv| (String::from_utf8(kv.key).unwrap(), String::from_utf8(kv.value).unwrap()))
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
