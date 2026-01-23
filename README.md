# 🛡️ File Integrity Monitor (FIM)
## منصة التحقيق الجنائي الرقمي المتقدمة | Advanced Digital Forensics Platform

<div align="center">
  <img width="1024" height="827" alt="pdf_report" src="https://github.com/user-attachments/assets/cc760685-d2d3-4af5-84b7-3eb6bae1b0d2" />

  <br><br>
  
  [![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue?style=for-the-badge&logo=python)](https://www.python.org/)
  [![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=for-the-badge&logo=windows)](https://www.microsoft.com/windows)
  [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
</div>

---

## 🌟 نظرة عامة | Overview

**File Integrity Monitor** هو نظام أمني متطور مصمم خصيصاً لفرق الأمن السيبراني والتحقيق الجنائي الرقمي. يقوم النظام بمراقبة ملفات النظام الحساسة في الوقت الفعلي، واكتشاف أي تعديلات غير مصرح بها بدقة متناهية، مع تحديد "المتسبب" (Actor) واستعادة الملفات المتضررة فوراً.

> **Advanced Real-time Integrity Monitoring System with Forensic Capabilities.**

[📘 **دليل المستخدم وتشغيل النظام | User Manual & Training Guide**](USER_MANUAL.md)

---

## 📸 جولة في النظام | Visual Tour

### 🖥️ لوحة القيادة الرئيسية (Main Dashboard)
واجهة تحكم مركزية تعرض حالة المراقبة الحية، مع رسوم بيانية تفاعلية لتوزيع الملفات وحالة النظام.
<div align="center">
<img width="1024" height="364" alt="main_window" src="https://github.com/user-attachments/assets/d1bfb653-b9a9-4759-8a5b-93a5201f19e6" />
</div>

<br>

### 🚨 مركز إدارة التنبيهات (Alerts Management)
سجل دقيق لكل عملية (تعديل، حذف، إنشاء) مع تحديد هوية البرنامج المسؤول (Process Name/ID) والمسار الكامل.
<div align="center">
<img width="897" height="533" alt="alerts_management" src="https://github.com/user-attachments/assets/704bfca9-b46b-4c2e-abbb-1c3460cdaf9f" />
</div>

<br>

### 📄 التقارير الجنائية (Forensic Reports)
توليد تقارير PDF احترافية ثنائية اللغة (عربي/إنجليزي) تتضمن تحليلاً شاملاً للأحداث، جاهزة للتقديم للجهات الرقابية.
<div align="center">
<img width="1024" height="827" alt="pdf_report" src="https://github.com/user-attachments/assets/926f4156-5a06-4cac-8531-0974e54dd46d" />
  <br>
<img width="1024" height="827" alt="pdf_report2" src="https://github.com/user-attachments/assets/d94f40f1-6bce-473d-afac-f5728956514c" />


</div>

---

## 🚀 الميزات الأساسية | Key Features

| الميزة (Feature) | الوصف (Description) |
| :--- | :--- |
| **🔍 Real-time Monitoring** | مراقبة فورية باستخدام خوارزميات `Watchdog` المتطورة لاكتشاف التغييرات في أجزاء من الثانية. |
| **🕵️ Forensic Actor** | ميزة فريدة لتحديد **البرنامج** أو **المستخدم** الذي قام بالتعديل (Process Tracking). |
| **🛡️ Ransomware Protection** | حماية ضد برمجيات الفدية عبر اكتشاف التشفير الجماعي السريع للملفات. |
| **⏪ Auto-Restore** | إمكانية "العودة بالزمن" واسترجاع النسخ الأصلية للملفات التي تم العبث بها. |
| **📊 Smart Reporting** | تقارير تحليلية شاملة بصيغة PDF مع رسوم بيانية وتفاصيل دقيقة. |

---

## 🏗️ هيكلية النظام | System Architecture

يوضح المخطط التالي تدفق البيانات من لحظة اكتشاف الحدث وحتى المعالجة والاستعادة:

```mermaid
graph TD
    %% Styles
    classDef monitor fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef engine fill:#004d99,stroke:#0066cc,stroke-width:2px,color:#fff;
    classDef db fill:#2d862d,stroke:#33cc33,stroke-width:2px,color:#fff;
    classDef ui fill:#4d0099,stroke:#6600cc,stroke-width:2px,color:#fff;

    Target[("📁 Target System")] --> Monitor["👁️ Watchdog Engine"]
    Monitor -- "Event Detected" --> Analysis["🧠 Forensic Analysis Core"]
    
    subgraph "Forensic Processing"
    Analysis --> Actor["🕵️ Identify Actor (Process)"]
    Analysis --> Hash["🔢 SHA-256 Hashing"]
    end
    
    Actor --> Database[("🗄️ Secure Database")]
    Hash --> Database
    
    Database --> Dashboard["🖥️ Admin Dashboard"]
    Dashboard -- "Restore Command" --> Recovery["⏪ Restoration Module"]
    Recovery --> Target

    class Monitor,Target monitor;
    class Analysis,Actor,Hash engine;
    class Database db;
    class Dashboard,Recovery ui;
```

---

## 🛠️ التثبيت والتشغيل | Installation

### متطلبات التشغيل (Requirements)
- Python 3.9+
- Windows 10/11

### 1. استنساخ المستودع (Clone)


### 2. إعداد البيئة الافتراضية (Setup)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. تشغيل النظام (Run)
```bash
python app.py
```
## ✍️ Engineer Development  | ✍️ تطوير المهندس
##  Mohammed Ameen Saleh Albareda  | محمد امين صالح البارده

Advanced AI Solutions Specialist | Cybersecurity Expert  
أخصائي حلول الذكاء الاصطناعي المتقدمة | متخصص في أمن سيبراني | Systems Architect 

[GitHub](https://github.com/775503801) | [LinkedIn](https://www.linkedin.com/in/Mohammed-Albareda) | [Instagram](https://www.instagram.com/mhmd.lbrdh?igsh=a2J4aXVidHpsb3Yw) | [Facebook](https://www.facebook.com/share/18Gh1EKFnP/)  

📧 mohmmedas2004@gmail.com | 📱 +967775503801

*Designing innovative AI solutions while securing digital systems to drive smart and safe technology.*
*أبتكر حلول ذكاء اصطناعي متقدمة وأؤمن الأنظمة الرقمية لتعزيز الأداء وحماية المعلومات.*





