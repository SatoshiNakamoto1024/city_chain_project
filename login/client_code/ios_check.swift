// File: client_code/ios_check.swift
// iOSアプリ (Swift) でストレージ空き容量を測定し、サーバーへ POST

import UIKit

class StorageCheckClient {
    
    static func getFreeSpaceBytes() -> Int64 {
        // Documents ディレクトリを対象に空き容量を取得
        guard let url = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return 0
        }
        do {
            let values = try url.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey])
            if let capacity = values.volumeAvailableCapacityForImportantUsageKey {
                return Int64(capacity)
            }
        } catch {
            print("Error retrieving volume capacity: \(error)")
        }
        return 0
    }
    
    static func doLogin(username: String, password: String) {
        let freeBytes = getFreeSpaceBytes()
        guard let url = URL(string: "http://your-server-ip:5050/login") else { return }
        
        // JSONボディを作成
        let jsonDict: [String: Any] = [
            "username": username,
            "password": password,
            "client_free_space": freeBytes
        ]
        
        guard let jsonData = try? JSONSerialization.data(withJSONObject: jsonDict) else { return }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")
        // iOS と判断されるように User-Agent を工夫
        request.addValue("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)", forHTTPHeaderField: "User-Agent")
        request.httpBody = jsonData
        
        let task = URLSession.shared.dataTask(with: request) { data, resp, err in
            if let err = err {
                print("Error: \(err)")
                return
            }
            if let data = data, let response = resp as? HTTPURLResponse {
                let body = String(data: data, encoding: .utf8) ?? ""
                print("Response code=\(response.statusCode), body=\(body)")
            }
        }
        task.resume()
    }
}
