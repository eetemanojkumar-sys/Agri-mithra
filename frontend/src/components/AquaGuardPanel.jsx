import React, { useState } from "react";
import axios from "axios";
import { AlertTriangle, CloudUpload, Droplets, Thermometer, ShieldCheck } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function AquaGuardPanel({ api, sensorData, selectedCrop = "general" }) {
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [message, setMessage] = useState("");
  const reading = {
    moisture: Number(sensorData?.moisture ?? 0),
    temperature: Number(sensorData?.temperature ?? 0),
    humidity: Number(sensorData?.humidity ?? 0),
    rain: Number(sensorData?.rain ?? 0),
    crop: selectedCrop || "general",
  };
  const analyze = async () => {
    setLoading(true); setMessage("");
    try {
      const response = await axios.post(api + "/aquaguard/analyze", reading);
      setAssessment(response.data);
    } catch (error) {
      setMessage(error.response?.data?.detail || "Could not analyze readings. Check that the updated backend is deployed.");
    } finally { setLoading(false); }
  };
  const archive = async () => {
    setArchiving(true); setMessage("");
    try {
      const response = await axios.post(api + "/aquaguard/telemetry", reading);
      setMessage(response.data.archived ? "Reading archived to S3: " + response.data.key : response.data.message || "S3 archiving is not configured yet.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "S3 archive failed. Check AWS configuration and IAM permissions.");
    } finally { setArchiving(false); }
  };
  const riskClass = (risk) => risk === "critical" || risk === "high" ? "text-red-600" : risk === "moderate" ? "text-amber-600" : "text-green-700";
  return (
    <section id="aquaguard" className="py-16 bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2"><Droplets className="h-8 w-8 text-primary" /><h2 className="text-3xl font-outfit font-bold text-primary">AquaGuard</h2></div>
          <p className="text-foreground/70 max-w-3xl">Climate-smart water conservation using current sensor readings, explainable risk rules, and optional AWS S3 telemetry archiving.</p>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card className="glass-card p-6 lg:col-span-2">
            <h3 className="text-lg font-outfit font-bold text-primary mb-4">Current sensor inputs</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                ["Soil moisture", reading.moisture + "%", Droplets],
                ["Temperature", reading.temperature + "°C", Thermometer],
                ["Humidity", reading.humidity + "%", ShieldCheck],
                ["Rain sensor", reading.rain + "%", AlertTriangle],
              ].map(([label, value, Icon]) => (
                <div key={label} className="rounded-xl bg-primary/5 p-4"><Icon className="h-5 w-5 text-primary mb-2" /><div className="text-xs text-foreground/60">{label}</div><div className="text-xl font-bold text-primary">{value}</div></div>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <Button onClick={analyze} disabled={loading}>{loading ? "Analyzing..." : "Assess water & heat risk"}</Button>
              <Button onClick={archive} disabled={archiving} variant="outline"><CloudUpload className="h-4 w-4 mr-2" />{archiving ? "Archiving..." : "Archive reading to AWS S3"}</Button>
            </div>
            {message && <p className="mt-4 text-sm text-foreground/80 break-words" role="status">{message}</p>}
          </Card>
          <Card className="glass-card p-6">
            <h3 className="text-lg font-outfit font-bold text-primary mb-4">Risk assessment</h3>
            {!assessment ? <p className="text-sm text-foreground/70">Run an assessment to see irrigation guidance and heat-risk signals.</p> : (
              <div>
                <div className="mb-4"><div className="text-sm text-foreground/60">Rule-based risk score</div><div className="text-4xl font-bold text-primary">{assessment.risk_score}<span className="text-lg">/100</span></div></div>
                <div className="space-y-2 mb-4">
                  <div>Water risk: <strong className={riskClass(assessment.water_risk)}>{assessment.water_risk}</strong></div>
                  <div>Heat risk: <strong className={riskClass(assessment.heat_risk)}>{assessment.heat_risk}</strong></div>
                  <div>Irrigation: <strong>{assessment.irrigation_recommended ? "Check and consider irrigation" : "Not currently indicated"}</strong></div>
                  <div className="text-xs text-foreground/60">Moisture trigger: {assessment.moisture_trigger_percent}% for {reading.crop}</div>
                </div>
                <ul className="list-disc pl-5 space-y-2 text-sm">{assessment.actions.map((action, index) => <li key={index}>{action}</li>)}</ul>
                <p className="mt-4 text-xs text-foreground/60">{assessment.disclaimer}</p>
              </div>
            )}
          </Card>
        </div>
        <p className="mt-4 text-xs text-foreground/60">AWS archival is optional. Configure the backend with a private S3 bucket and an IAM role or standard AWS credential chain. Never put AWS credentials in frontend code.</p>
      </div>
    </section>
  );
}
