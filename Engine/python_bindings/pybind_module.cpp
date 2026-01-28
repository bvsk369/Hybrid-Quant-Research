#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include "features.hpp"

namespace py = pybind11;

PYBIND11_MODULE(quant_engine, m) {
    m.doc() = "Quantitative Trading Engine - C++ Implementation";
    
    // Features module
    py::module_ features = m.def_submodule("features", "Technical indicators");
    
    features.def("sma", &quant::sma,
                 "Simple Moving Average",
                 py::arg("prices"), py::arg("period"));
    
    features.def("ema", &quant::ema,
                 "Exponential Moving Average",
                 py::arg("prices"), py::arg("period"));
    
    features.def("rsi", &quant::rsi,
                 "Relative Strength Index",
                 py::arg("prices"), py::arg("period") = 14);
    
    features.def("atr", &quant::atr,
                 "Average True Range",
                 py::arg("high"), py::arg("low"), py::arg("close"), py::arg("period") = 14);
    
    features.def("momentum", &quant::momentum,
                 "Momentum (Rate of Change)",
                 py::arg("prices"), py::arg("period"));
    
    features.def("rolling_std", &quant::rolling_std,
                 "Rolling Standard Deviation",
                 py::arg("values"), py::arg("period"));
    
    features.def("zscore", &quant::zscore,
                 "Z-Score",
                 py::arg("values"), py::arg("period"));
}
