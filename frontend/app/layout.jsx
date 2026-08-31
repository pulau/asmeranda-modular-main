import "./globals.css";
import MainLayout from "@/components/MainLayout";

export const metadata = {
  title: "Asmeranda AI — Machine Learning Platform",
  description:
    "Platform Machine Learning modular oleh PT. Asmer Sahabat Sukses. Upload dataset, EDA, preprocessing, training model, SHAP/LIME interpretasi, dan time series forecasting.",
  keywords: "machine learning, AI, data science, forecasting, anomaly detection",
};

export default function RootLayout({ children }) {
  return (
    <html lang="id">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#f8fbff" />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body>
        <MainLayout>{children}</MainLayout>
      </body>
    </html>
  );
}
