// D:\city_chain_project\Algorithm\EC\ec_rust_src\src\parallel.rs
//! Parallel helper utilities for EC operations.
//!
//! These enable sharding or other transforms to run over large inputs
//! using Rayon’s data‐parallel iterators.

use rayon::prelude::*;

/// Applies the function `f` to each element of `items` in parallel,
/// collecting the results into a `Vec<O>`.
///
/// # Examples
///
/// ```rust
/// let data = vec![1,2,3,4];
/// let squares = parallel_map(&data, |x| x * x);
/// assert_eq!(squares, vec![1,4,9,16]);
/// ```
pub fn parallel_map<I, O, F>(items: &[I], f: F) -> Vec<O>
where
    I: Sync,
    O: Send,
    F: Fn(&I) -> O + Sync,
{
    items.par_iter().map(|i| f(i)).collect()
}
