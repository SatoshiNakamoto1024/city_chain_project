// D:\city_chain_project\DAGs\libs\algorithm\poh_holdmetrics\poh_holdmetrics_rust\src\bindings.rs
#![cfg(any(feature = "python", feature = "py-ext"))]

use std::sync::Arc;

use chrono::{DateTime, Utc};
use pyo3::{
    exceptions::PyValueError,
    prelude::*,
    types::PyModule,
    Bound, PyErr, PyRef, PyResult, Python,
    wrap_pyfunction,
};
use pyo3_async_runtimes::tokio::future_into_py;

use crate::{calc_score, holdset::HoldAggregator, model::HoldEvent};

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
        Self {
            token_id,
            holder_id,
            start,
            end,
            weight: weight.unwrap_or(1.0),
        }
    }
}

fn ts(sec: i64) -> Result<DateTime<Utc>, PyErr> {
    DateTime::<Utc>::from_timestamp(sec, 0)
        .ok_or_else(|| PyValueError::new_err("invalid unix timestamp"))
}

impl TryFrom<&PyHoldEvent> for HoldEvent {
    type Error = PyErr;

    fn try_from(p: &PyHoldEvent) -> Result<Self, Self::Error> {
        let start = ts(p.start)?;
        let end = match p.end {
            Some(e) => Some(ts(e)?),
            None => None,
        };
        Ok(HoldEvent {
            token_id: p.token_id.clone(),
            holder_id: p.holder_id.clone(),
            start,
            end,
            weight: p.weight,
        })
    }
}

#[pyclass]
pub struct PyAggregator {
    inner: Arc<HoldAggregator>,
}

#[pymethods]
impl PyAggregator {
    #[new]
    fn new() -> Self {
        Self {
            inner: Arc::new(HoldAggregator::default()),
        }
    }

    /// awaitable: `await agg.record(event)`
    /// GIL 中に Rust 構造体へ変換してから async に渡す
    fn record<'py>(&self, py: Python<'py>, ev: Py<PyHoldEvent>) -> PyResult<Bound<'py, pyo3::PyAny>> {
        let ev_rs: HoldEvent = {
            let ev_ref: PyRef<PyHoldEvent> = ev.bind(py).borrow();
            (&*ev_ref).try_into()?
        };

        let inner = Arc::clone(&self.inner);
        // PyO3 0.22 では Bound<'py, PyAny> を返す
        future_into_py(py, async move {
            inner
                .record(&ev_rs)
                .map_err(|e| PyValueError::new_err(e.to_string()))?;
            Ok(()) // await の結果は None
        })
    }

    /// 同期版
    fn record_sync(&self, py: Python<'_>, ev: Py<PyHoldEvent>) -> PyResult<()> {
        let ev_ref: PyRef<PyHoldEvent> = ev.bind(py).borrow();
        let ev_rs: HoldEvent = (&*ev_ref).try_into()?;
        self.inner
            .record(&ev_rs)
            .map_err(|e| PyValueError::new_err(e.to_string()))
    }

    fn snapshot(&self) -> Vec<(String, f64)> {
        self.inner
            .snapshot()
            .into_iter()
            .map(|s| (s.holder_id, s.weighted_score))
            .collect()
    }
}

#[pyfunction]
fn calculate_score(py: Python<'_>, events: Vec<Py<PyHoldEvent>>) -> PyResult<f64> {
    let mut native = Vec::with_capacity(events.len());
    for obj in events {
        let ev_ref: PyRef<PyHoldEvent> = obj.bind(py).borrow();
        native.push((&*ev_ref).try_into()?);
    }
    calc_score(&native).map_err(|e| PyValueError::new_err(e.to_string()))
}

#[pymodule]
fn poh_holdmetrics_rust(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyHoldEvent>()?;
    m.add_class::<PyAggregator>()?;
    m.add_function(wrap_pyfunction!(calculate_score, m)?)?;
    Ok(())
}
