// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\bindings.rs
#![cfg(any(feature = "python", feature = "python-ext"))]

// ── 追加 / 修正インポート ────────────────────────────────────────────────
use chrono::{DateTime, Utc};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::{PyAny, PyModule},
    Bound,                // ★ 追加
    PyErr, PyRef, PyResult, Python,
    wrap_pyfunction,      // ★ 追加
};
use pyo3_async_runtimes::tokio::future_into_py;
use std::sync::Arc;

use crate::{calc_score, holdset::HoldAggregator, model::HoldEvent};

// ── PyHoldEvent ────────────────────────────────────────────────────────────
#[pyclass]
#[derive(Clone)]
pub struct PyHoldEvent {
    #[pyo3(get)]
    token_id: String,
    #[pyo3(get)]
    holder_id: String,
    #[pyo3(get)]
    start: i64,
    #[pyo3(get)]
    end: Option<i64>,
    #[pyo3(get)]
    weight: f64,
}

#[pymethods]
impl PyHoldEvent {
    #[new]
    fn new(
        token_id: String,
        holder_id: String,
        start: i64,
        end: Option<i64>,
        weight: Option<f64>,
    ) -> Self {
        Self { token_id, holder_id, start, end, weight: weight.unwrap_or(1.0) }
    }
}

impl From<&PyHoldEvent> for HoldEvent {
    fn from(p: &PyHoldEvent) -> Self {
        let ts = |sec| DateTime::<Utc>::from_timestamp(sec, 0).unwrap();
        HoldEvent {
            token_id: p.token_id.clone(),
            holder_id: p.holder_id.clone(),
            start: ts(p.start),
            end: p.end.map(ts),
            weight: p.weight,
        }
    }
}

// ── PyAggregator ──────────────────────────────────────────────────────────
#[pyclass]
pub struct PyAggregator {
    inner: Arc<HoldAggregator>,
}

#[pymethods]
impl PyAggregator {
    #[new]
    fn new() -> Self {
        Self { inner: Arc::new(HoldAggregator::default()) }
    }

    /// awaitable: await agg.record(event)
    fn record<'py>(&self, py: Python<'py>, ev: Py<PyHoldEvent>) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        future_into_py(py, async move {
            Python::with_gil(|py| {
                let ev_ref: PyRef<PyHoldEvent> = ev.bind(py).extract()?;
                let ev_rs: HoldEvent = (&*ev_ref).into();
                inner
                    .record(&ev_rs)
                    .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))
            })
        })
    }

    /// 同期版: await を使わずに1件登録する
    fn record_sync(&self, py: Python<'_>, ev: Py<PyHoldEvent>) -> PyResult<()> {
        let ev_ref: PyRef<PyHoldEvent> = ev.bind(py).extract()?;
        let ev_rs: HoldEvent = (&*ev_ref).into();
        self.inner
            .record(&ev_rs)
            .map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))?;
        Ok(())
    }

    fn snapshot(&self) -> Vec<(String, f64)> {
        self.inner
            .snapshot()
            .into_iter()
            .map(|s| (s.holder_id, s.weighted_score))
            .collect()
    }
}

// ── calculate_score ───────────────────────────────────────────────────────
#[pyfunction]
fn calculate_score(py: Python<'_>, events: Vec<Py<PyHoldEvent>>) -> PyResult<f64> {
    let mut native = Vec::with_capacity(events.len());
    for obj in events {
        let ev_ref: PyRef<PyHoldEvent> = obj.bind(py).extract()?;
        native.push((&*ev_ref).into());
    }
    calc_score(&native).map_err(|e| PyErr::new::<PyValueError, _>(e.to_string()))
}

// ── pymodule エントリ ────────────────────────────────────────────────────
#[pymodule]
fn poh_holdmetrics_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyHoldEvent>()?;
    m.add_class::<PyAggregator>()?;
    m.add_function(wrap_pyfunction!(calculate_score, m)?)?;
    Ok(())
}
