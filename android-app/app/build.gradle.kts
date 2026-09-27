plugins {
    id("com.android.application")
}

android {
    namespace = "cn.mingjian.legal"
    compileSdk = 36

    defaultConfig {
        applicationId = "cn.mingjian.legal"
        minSdk = 24
        targetSdk = 36
        versionCode = 2
        versionName = "1.1.0"

        buildConfigField("String", "APP_URL", "\"http://39.96.14.33/\"")
    }

    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("androidx.activity:activity:1.11.0")
    implementation("androidx.core:core:1.17.0")
}
