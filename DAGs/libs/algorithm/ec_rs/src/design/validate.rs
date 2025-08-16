// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\design\validate.rs
//! 行列の簡易バリデータ

use super::qcpeg::SparseMatrix;

/// 非ゼロのサイクル長 (girth) を BFS でざっくり推定
pub fn girth(h: &SparseMatrix) -> usize {
    let m = h.len();
    let mut min_cycle = usize::MAX;

    for start in 0..m {
        let mut visited = vec![false; m];
        let mut queue = std::collections::VecDeque::new();
        queue.push_back((start, usize::MAX, 0usize)); // (row, prev_col, depth)

        while let Some((r, prev_c, depth)) = queue.pop_front() {
            if depth >= min_cycle { continue; }
            visited[r] = true;
            for &(c, _) in &h[r] {
                if c == prev_c { continue; }
                // 辺 (r,c) から隣接行へ
                for (next_r, row) in h.iter().enumerate() {
                    if next_r == r { continue; }
                    if row.iter().any(|&(cc, _)| cc == c) {
                        if next_r == start && depth >= 2 {
                            min_cycle = min_cycle.min(depth + 1);
                        } else if !visited[next_r] {
                            queue.push_back((next_r, c, depth + 1));
                        }
                    }
                }
            }
        }
    }
    if min_cycle == usize::MAX { 0 } else { min_cycle }
}
