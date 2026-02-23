import { useState, useEffect, useRef } from "react";
import "@/App.css";
import { motion } from "framer-motion";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import {
  Droplets,
  Thermometer,
  CloudRain,
  Wind,
  Power,
  TrendingUp,
  Sprout,
  Zap,
  CheckCircle2,
  AlertTriangle,
  Wifi,
  WifiOff,
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import axios from "axios";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  // Sensor data state
  const [sensorData, setSensorData] = useState({
    moisture: 45,
    temperature: 28,
    humidity: 65,
    rain: 20,
  });

  // Motor state
  const [motorRunning, setMotorRunning] = useState(false);

  // ThingSpeak configuration
  const [channelId, setChannelId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [isLiveMode, setIsLiveMode] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [connecting, setConnecting] = useState(false);
  const [simulatorMode, setSimulatorMode] = useState(true);

  // Commodity price state
  const [selectedCrop, setSelectedCrop] = useState("rice");
  const [priceData, setPriceData] = useState(null);
  const [loadingPrice, setLoadingPrice] = useState(false);

  // AI Analysis state
  const [agriAnalysis, setAgriAnalysis] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [showDetailedAnalysis, setShowDetailedAnalysis] = useState(false);

  const pollIntervalRef = useRef(null);

  // Demo mode simulation
  useEffect(() => {
    if (simulatorMode && !isLiveMode) {
      const demoInterval = setInterval(() => {
        setSensorData({
          moisture: Math.floor(Math.random() * 40) + 20,
          temperature: Math.floor(Math.random() * 15) + 20,
          humidity: Math.floor(Math.random() * 30) + 50,
          rain: Math.floor(Math.random() * 30),
        });
        setLastUpdated(new Date());
      }, 5000);

      return () => clearInterval(demoInterval);
    }
  }, [simulatorMode, isLiveMode]);

  // Fetch commodity price data
  useEffect(() => {
    fetchCommodityPrices(selectedCrop);
  }, [selectedCrop]);

  // Fetch AI analysis when sensor data changes
  useEffect(() => {
    fetchAgriAnalysis();
  }, [sensorData]);

  const fetchAgriAnalysis = async () => {
    setAnalysisLoading(true);
    try {
      const response = await axios.post(`${API}/agri-analysis`, {
        moisture: sensorData.moisture,
        temperature: sensorData.temperature,
        humidity: sensorData.humidity,
      });
      setAgriAnalysis(response.data);
    } catch (error) {
      console.error("Error fetching agricultural analysis:", error);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const fetchCommodityPrices = async (crop) => {
    setLoadingPrice(true);
    try {
      const response = await axios.get(`${API}/commodity-prices/${crop}`);
      setPriceData(response.data);
    } catch (error) {
      console.error("Error fetching commodity prices:", error);
    } finally {
      setLoadingPrice(false);
    }
  };

  const connectThingSpeak = async () => {
    if (!channelId || !apiKey) {
      alert("Please enter both Channel ID and API Key");
      return;
    }

    setConnecting(true);
    try {
      const response = await axios.post(`${API}/thingspeak/fetch`, {
        channel_id: channelId,
        read_api_key: apiKey,
      });

      if (response.data.success) {
        setSensorData(response.data.data);
        setIsLiveMode(true);
        setSimulatorMode(false);
        setLastUpdated(new Date());

        // Start polling every 20 seconds
        if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = setInterval(async () => {
          try {
            const pollResponse = await axios.post(`${API}/thingspeak/fetch`, {
              channel_id: channelId,
              read_api_key: apiKey,
            });
            if (pollResponse.data.success) {
              setSensorData(pollResponse.data.data);
              setLastUpdated(new Date());
            }
          } catch (err) {
            console.error("Polling error:", err);
          }
        }, 20000);
      }
    } catch (error) {
      console.error("ThingSpeak connection error:", error);
      alert("Failed to connect to ThingSpeak. Please check your credentials.");
    } finally {
      setConnecting(false);
    }
  };

  const toggleMotor = async () => {
    try {
      const newStatus = !motorRunning;
      await axios.post(`${API}/motor/control`, {
        status: newStatus ? "on" : "off",
      });
      setMotorRunning(newStatus);
    } catch (error) {
      console.error("Motor control error:", error);
    }
  };

  const getSensorStatus = (value, type) => {
    if (type === "moisture") {
      if (value < 30) return "low";
      if (value > 70) return "high";
      return "normal";
    }
    if (type === "temperature") {
      if (value > 35) return "high";
      if (value < 20) return "low";
      return "normal";
    }
    if (type === "humidity") {
      if (value > 80) return "high";
      if (value < 40) return "low";
      return "normal";
    }
    if (type === "rain") {
      if (value > 50) return "high";
      if (value < 20) return "low";
      return "normal";
    }
    return "normal";
  };

  const getStatusBadge = (status) => {
    if (status === "high") return "status-badge-high";
    if (status === "low") return "status-badge-low";
    return "status-badge-normal";
  };

  const getStatusLabel = (status) => {
    if (status === "high") return "High";
    if (status === "low") return "Low";
    return "Normal";
  };

  const scrollToSection = (id) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  };

  const chartData = priceData
    ? {
        labels: priceData.dates,
        datasets: [
          {
            label: `${priceData.crop} Price (₹/quintal)`,
            data: priceData.prices,
            borderColor: "#2F5D41",
            backgroundColor: "rgba(47, 93, 65, 0.1)",
            fill: true,
            tension: 0.4,
            pointRadius: 5,
            pointHoverRadius: 7,
          },
        ],
      }
    : null;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: "top",
      },
      tooltip: {
        mode: "index",
        intersect: false,
      },
    },
    scales: {
      y: {
        beginAtZero: false,
      },
    },
  };

  return (
    <div className="min-h-screen grain-texture bg-background">
      {/* Sticky Navbar */}
      <nav className="sticky top-0 z-50 nav-blur">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Sprout className="h-8 w-8 text-primary" />
              <h1 className="text-2xl font-outfit font-bold text-primary tracking-tight">
                AgriSmart
              </h1>
            </div>
            <div className="flex items-center gap-6">
              <button
                data-testid="nav-monitoring-btn"
                onClick={() => scrollToSection("monitoring")}
                className="text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                Dashboard
              </button>
              <button
                data-testid="nav-prices-btn"
                onClick={() => scrollToSection("prices")}
                className="text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                Market Forecast
              </button>
              <button
                onClick={() => scrollToSection("config")}
                className="text-sm font-medium text-foreground hover:text-primary transition-colors"
              >
                IoT Setup
              </button>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10">
                {isLiveMode ? (
                  <>
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" data-testid="live-indicator" />
                    <span className="text-xs font-semibold text-primary" data-testid="mode-label">
                      LIVE
                    </span>
                  </>
                ) : simulatorMode ? (
                  <>
                    <Zap className="h-3 w-3 text-accent" data-testid="simulator-indicator" />
                    <span className="text-xs font-semibold text-accent" data-testid="mode-label">
                      SIMULATOR
                    </span>
                  </>
                ) : (
                  <>
                    <WifiOff className="h-3 w-3 text-gray-400" />
                    <span className="text-xs font-medium text-gray-600">OFFLINE</span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-gradient py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center max-w-4xl mx-auto"
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-outfit font-bold text-primary tracking-tight mb-6">
              Smart Crop Irrigation Monitoring & Commodity Price Predictor
            </h1>
            <p className="text-base sm:text-lg text-foreground/80 mb-12 max-w-2xl mx-auto">
              IoT + Machine Learning based Smart Agriculture System for optimized
              water usage and market insights
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button
                data-testid="hero-monitoring-btn"
                onClick={() => scrollToSection("monitoring")}
                className="bg-primary hover:bg-primary/90 text-white px-8 py-6 text-base rounded-full font-medium transition-all hover:scale-105"
                size="lg"
              >
                View Live Monitoring
              </Button>
              <Button
                data-testid="hero-forecast-btn"
                onClick={() => scrollToSection("prices")}
                variant="outline"
                className="border-2 border-primary text-primary hover:bg-primary hover:text-white px-8 py-6 text-base rounded-full font-medium transition-all hover:scale-105"
                size="lg"
              >
                Check Price Forecast
              </Button>
            </div>
          </motion.div>

          {/* Stats Grid */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20"
          >
            {[
              { label: "Water Saved", value: "40%", icon: Droplets },
              { label: "Accuracy", value: "95%", icon: CheckCircle2 },
              { label: "Monitoring", value: "24/7", icon: Zap },
              { label: "Crops Supported", value: "5+", icon: Sprout },
            ].map((stat, idx) => (
              <motion.div
                key={idx}
                whileHover={{ scale: 1.05 }}
                className="glass-card p-6 rounded-xl text-center"
                data-testid={`stat-card-${idx}`}
              >
                <stat.icon className="h-8 w-8 text-primary mx-auto mb-3" />
                <div className="text-3xl font-outfit font-bold text-primary mb-1">
                  {stat.value}
                </div>
                <div className="text-sm text-foreground/70">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Monitoring Dashboard */}
      <section id="monitoring" className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-outfit font-bold text-primary mb-4">
              Real-Time Monitoring Dashboard
            </h2>
            <p className="text-base text-foreground/70">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          </div>

          {/* Sensor Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
            {[
              {
                icon: Droplets,
                label: "Soil Moisture",
                value: sensorData.moisture,
                unit: "%",
                type: "moisture",
                color: "#3B82F6",
              },
              {
                icon: Thermometer,
                label: "Temperature",
                value: sensorData.temperature,
                unit: "°C",
                type: "temperature",
                color: "#EF4444",
              },
              {
                icon: Wind,
                label: "Humidity",
                value: sensorData.humidity,
                unit: "%",
                type: "humidity",
                color: "#10B981",
              },
              {
                icon: CloudRain,
                label: "Rain Sensor",
                value: sensorData.rain,
                unit: "%",
                type: "rain",
                color: "#8B5CF6",
              },
            ].map((sensor, idx) => {
              const status = getSensorStatus(sensor.value, sensor.type);
              return (
                <motion.div
                  key={idx}
                  whileHover={{ y: -5 }}
                  transition={{ duration: 0.2 }}
                  data-testid={`sensor-card-${sensor.type}`}
                >
                  <Card className="glass-card p-6 h-full">
                    <div className="flex items-center justify-between mb-4">
                      <sensor.icon
                        className="h-10 w-10"
                        style={{ color: sensor.color }}
                      />
                      <span
                        className={getStatusBadge(status)}
                        data-testid={`sensor-status-${sensor.type}`}
                      >
                        {getStatusLabel(status)}
                      </span>
                    </div>
                    <div className="mb-2">
                      <div className="text-sm font-medium text-foreground/70 mb-1">
                        {sensor.label}
                      </div>
                      <div className="text-4xl font-mono font-bold text-primary">
                        {sensor.value}
                        <span className="text-2xl">{sensor.unit}</span>
                      </div>
                    </div>
                    <div className="mt-4">
                      <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${sensor.value}%`,
                            backgroundColor: sensor.color,
                          }}
                          data-testid={`sensor-progress-${sensor.type}`}
                        />
                      </div>
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Motor Control & AI Recommendation */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Motor Control */}
            <Card className="glass-card p-8">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <Power className="h-8 w-8 text-primary" />
                  <h3 className="text-xl font-outfit font-bold text-primary">
                    Motor Control
                  </h3>
                </div>
                <div className="flex items-center gap-3">
                  {motorRunning && (
                    <div
                      className="w-3 h-3 bg-green-500 rounded-full motor-running"
                      data-testid="motor-indicator"
                    />
                  )}
                  <Switch
                    checked={motorRunning}
                    onCheckedChange={toggleMotor}
                    data-testid="motor-toggle"
                  />
                </div>
              </div>
              <div className="text-center py-8">
                <div
                  className={`text-2xl font-outfit font-bold mb-2 ${
                    motorRunning ? "text-green-600" : "text-gray-400"
                  }`}
                  data-testid="motor-status-text"
                >
                  {motorRunning ? "Motor Running" : "Motor Stopped"}
                </div>
                <p className="text-sm text-foreground/70">
                  {motorRunning
                    ? "Irrigation system is active"
                    : "Toggle switch to start irrigation"}
                </p>
              </div>
            </Card>

            {/* AI Recommendation */}
            <Card className="glass-card p-8">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <Sprout className="h-8 w-8 text-primary" />
                  <h3 className="text-xl font-outfit font-bold text-primary">
                    AI Decision Support
                  </h3>
                </div>
                <Button
                  data-testid="view-detailed-analysis-btn"
                  onClick={() => setShowDetailedAnalysis(!showDetailedAnalysis)}
                  variant="outline"
                  size="sm"
                  className="text-xs"
                >
                  {showDetailedAnalysis ? "Quick View" : "Detailed Analysis"}
                </Button>
              </div>

              {analysisLoading ? (
                <div className="text-center py-8">
                  <div className="inline-block w-6 h-6 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                </div>
              ) : agriAnalysis ? (
                <div>
                  {!showDetailedAnalysis ? (
                    <div className="text-center py-8" data-testid="quick-recommendation">
                      {agriAnalysis.irrigation_decision.irrigation_needed ? (
                        <div>
                          <AlertTriangle className="h-16 w-16 text-accent mx-auto mb-4" />
                          <div className="text-2xl font-outfit font-bold text-accent mb-2">
                            {agriAnalysis.irrigation_decision.urgency === "immediate"
                              ? "Irrigate Now!"
                              : "Irrigation Recommended"}
                          </div>
                          <p className="text-foreground/70 mb-4">
                            {agriAnalysis.irrigation_decision.reasoning}
                          </p>
                          <div className="text-sm text-foreground/60">
                            Apply: {agriAnalysis.irrigation_decision.recommended_water_amount}
                          </div>
                        </div>
                      ) : (
                        <div>
                          <CheckCircle2 className="h-16 w-16 text-green-600 mx-auto mb-4" />
                          <div className="text-2xl font-outfit font-bold text-green-600 mb-2">
                            Optimal Conditions
                          </div>
                          <p className="text-foreground/70 mb-4">
                            {agriAnalysis.irrigation_decision.reasoning}
                          </p>
                          <div className="text-sm text-foreground/60">
                            {agriAnalysis.yield_insight.growth_description}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-6 max-h-96 overflow-y-auto" data-testid="detailed-analysis">
                      {/* Environmental Assessment */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Environmental Assessment
                        </h4>
                        <div className="space-y-1 text-sm">
                          <p>• {agriAnalysis.environmental_assessment.soil_description}</p>
                          <p>• {agriAnalysis.environmental_assessment.temp_description}</p>
                          <p>• {agriAnalysis.environmental_assessment.humidity_description}</p>
                        </div>
                      </div>

                      {/* Crop Recommendation */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Crop Recommendation
                        </h4>
                        <div className="flex flex-wrap gap-2 mb-2">
                          {agriAnalysis.crop_recommendation.recommended_crops.map((crop, idx) => (
                            <span
                              key={idx}
                              className="px-3 py-1 bg-primary/10 text-primary rounded-full text-sm font-medium"
                            >
                              {crop}
                            </span>
                          ))}
                        </div>
                        <p className="text-sm text-foreground/70">
                          {agriAnalysis.crop_recommendation.reasoning}
                        </p>
                      </div>

                      {/* Yield Insight */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Yield & Growth Insight
                        </h4>
                        <div className="space-y-1 text-sm">
                          <p className="font-medium">Status: {agriAnalysis.yield_insight.yield_status}</p>
                          <p>Predicted Yield: {agriAnalysis.yield_insight.predicted_yield}</p>
                          <p>{agriAnalysis.yield_insight.growth_description}</p>
                        </div>
                      </div>

                      {/* Risk Detection */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Risk Detection ({agriAnalysis.risk_detection.risk_count} active)
                        </h4>
                        <div className="space-y-2">
                          {agriAnalysis.risk_detection.identified_risks.map((risk, idx) => (
                            <div
                              key={idx}
                              className={`p-2 rounded text-sm ${
                                risk.severity === "high"
                                  ? "bg-red-50 border border-red-200"
                                  : risk.severity === "medium"
                                  ? "bg-yellow-50 border border-yellow-200"
                                  : "bg-green-50 border border-green-200"
                              }`}
                            >
                              <span className="font-medium">{risk.type}</span>: {risk.description}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Corrective Actions */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Corrective Actions
                        </h4>
                        <ul className="space-y-1 text-sm">
                          {agriAnalysis.corrective_actions.map((action, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                              <span>{action}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Fertilizer Advisory */}
                      <div>
                        <h4 className="font-outfit font-bold text-primary mb-2">
                          Fertilizer Advisory
                        </h4>
                        <ul className="space-y-1 text-sm">
                          {agriAnalysis.fertilizer_advisory.recommendations.map((rec, idx) => (
                            <li key={idx}>• {rec}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-foreground/70">Loading analysis...</p>
                </div>
              )}
            </Card>
          </div>
        </div>
      </section>

      {/* Configuration Panel */}
      <section className="py-16 lg:py-24 bg-secondary/30">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-outfit font-bold text-primary mb-4">
              Cloud Connection Setup
            </h2>
            <p className="text-base text-foreground/70">
              Connect to ThingSpeak for live sensor data
            </p>
          </div>

          <Card className="glass-card p-8">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  ThingSpeak Channel ID
                </label>
                <Input
                  data-testid="channel-id-input"
                  type="text"
                  placeholder="Enter Channel ID"
                  value={channelId}
                  onChange={(e) => setChannelId(e.target.value)}
                  className="h-12"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Read API Key
                </label>
                <Input
                  data-testid="api-key-input"
                  type="text"
                  placeholder="Enter Read API Key"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="h-12"
                />
              </div>
              <Button
                data-testid="connect-btn"
                onClick={connectThingSpeak}
                disabled={connecting || isLiveMode}
                className="w-full bg-primary hover:bg-primary/90 text-white h-12 font-medium"
              >
                {connecting
                  ? "Connecting..."
                  : isLiveMode
                  ? "Connected"
                  : "Connect"}
              </Button>
              {isLiveMode && (
                <p
                  className="text-center text-sm text-green-600 font-medium"
                  data-testid="connected-message"
                >
                  Successfully connected! Data updates every 20 seconds.
                </p>
              )}
            </div>
          </Card>
        </div>
      </section>

      {/* Hardware Setup Guide */}
      <section className="py-16 lg:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-outfit font-bold text-primary mb-4">
              Hardware Setup Guide
            </h2>
            <p className="text-base text-foreground/70">
              Follow these steps to set up your IoT monitoring system
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                step: "1",
                title: "Create ThingSpeak Channel",
                description:
                  "Sign up on ThingSpeak.com and create a new channel with 4 fields: Moisture, Temperature, Humidity, Rain",
              },
              {
                step: "2",
                title: "Upload ESP32 Code",
                description:
                  "Flash your ESP32/NodeMCU with the sensor reading code and ThingSpeak API integration",
              },
              {
                step: "3",
                title: "Wire Sensors",
                description:
                  "Connect sensors to GPIO pins: Moisture (34), Temperature (4), Humidity (35), Rain (5)",
              },
              {
                step: "4",
                title: "Start Monitoring",
                description:
                  "Enter your Channel ID and API Key above to begin real-time monitoring",
              },
            ].map((item, idx) => (
              <motion.div
                key={idx}
                whileHover={{ scale: 1.05 }}
                data-testid={`setup-step-${idx}`}
              >
                <Card className="glass-card p-6 h-full">
                  <div className="w-12 h-12 rounded-full bg-primary text-white flex items-center justify-center text-xl font-bold mb-4">
                    {item.step}
                  </div>
                  <h3 className="text-lg font-outfit font-bold text-primary mb-2">
                    {item.title}
                  </h3>
                  <p className="text-sm text-foreground/70">{item.description}</p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Commodity Price Prediction */}
      <section id="prices" className="py-16 lg:py-24 bg-secondary/30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-outfit font-bold text-primary mb-4">
              Commodity Price Prediction
            </h2>
            <p className="text-base text-foreground/70">
              7-day ML-based price forecast with buy/sell recommendations
            </p>
          </div>

          {/* Crop Selection */}
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {["rice", "onion", "tomato", "cotton", "groundnut"].map((crop) => (
              <Button
                key={crop}
                data-testid={`crop-btn-${crop}`}
                onClick={() => setSelectedCrop(crop)}
                variant={selectedCrop === crop ? "default" : "outline"}
                className={`${
                  selectedCrop === crop
                    ? "bg-primary text-white"
                    : "border-primary text-primary hover:bg-primary hover:text-white"
                } px-6 py-3 rounded-full font-medium transition-all hover:scale-105`}
              >
                {crop.charAt(0).toUpperCase() + crop.slice(1)}
              </Button>
            ))}
          </div>

          {/* Chart and Recommendation */}
          {priceData && !loadingPrice && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Chart */}
              <Card className="glass-card p-8 lg:col-span-2">
                <h3 className="text-xl font-outfit font-bold text-primary mb-6">
                  7-Day Price Forecast
                </h3>
                <div className="h-80" data-testid="price-chart">
                  <Line data={chartData} options={chartOptions} />
                </div>
              </Card>

              {/* Recommendation Card */}
              <div className="space-y-6">
                <Card className="glass-card p-8">
                  <div className="flex items-center gap-3 mb-6">
                    <TrendingUp className="h-8 w-8 text-primary" />
                    <h3 className="text-xl font-outfit font-bold text-primary">
                      Recommendation
                    </h3>
                  </div>
                  <div className="text-center py-4">
                    <div
                      className={`text-2xl font-outfit font-bold mb-2 ${
                        priceData.change_percent > 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                      data-testid="recommendation-text"
                    >
                      {priceData.recommendation}
                    </div>
                    <p className="text-sm text-foreground/70 mb-4">
                      Expected change: {priceData.change_percent > 0 ? "+" : ""}
                      {priceData.change_percent}%
                    </p>
                  </div>
                </Card>

                <Card className="glass-card p-8">
                  <h3 className="text-lg font-outfit font-bold text-primary mb-4">
                    Quick Stats
                  </h3>
                  <div className="space-y-4">
                    <div data-testid="current-price">
                      <div className="text-sm text-foreground/70">Current Price</div>
                      <div className="text-2xl font-mono font-bold text-primary">
                        ₹{priceData.current_price}
                      </div>
                    </div>
                    <div data-testid="forecast-price">
                      <div className="text-sm text-foreground/70">Day 7 Forecast</div>
                      <div className="text-2xl font-mono font-bold text-primary">
                        ₹{priceData.forecast_price}
                      </div>
                    </div>
                    <div data-testid="accuracy">
                      <div className="text-sm text-foreground/70">
                        Model Accuracy
                      </div>
                      <div className="text-2xl font-mono font-bold text-green-600">
                        {priceData.accuracy}%
                      </div>
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {loadingPrice && (
            <div className="text-center py-12">
              <div className="inline-block w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-primary text-white py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <Sprout className="h-8 w-8" />
            <h3 className="text-2xl font-outfit font-bold">AgriSmart</h3>
          </div>
          <p className="text-white/80 mb-2">
            IoT + Machine Learning for Smart Agriculture
          </p>
          <p className="text-sm text-white/60">
            © 2026 AgriSmart. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
