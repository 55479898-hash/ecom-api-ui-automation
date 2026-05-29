# 电商交易链路接口自动化与性能测试框架

## 技术栈

Python · pytest · requests · Allure · PyMySQL · JSON Schema · Playwright · JMeter · GitHub Actions

## 项目结构

```
ecom_app/                 # 被测系统（登录/商品/购物车/下单/支付回调/取消订单）
automation_tests/
  api/                    # 接口自动化
  ui/                     # UI 自动化
  utils/                  # ApiClient、DbHelper、Schema 校验
  config/environments.yaml # 多环境配置
  schemas/                # JSON Schema
jmeter/                   # 性能测试说明
.github/workflows/ci.yml  # CI 流水线
```

## 快速开始

```powershell
pip install -r ecom_app/requirements.txt -r automation_tests/requirements.txt
python -m playwright install chromium
cd automation_tests
pytest api/ -m api
pytest ui/ -m ui
```

## Allure 报告

```powershell
pytest api/ -m api
allure serve reports/allure-results
```

## 测试能力

- pytest + requests 封装 ApiClient，支持多环境、鉴权、日志
- JSON Schema 校验响应结构
- DbHelper 数据库断言（SQLite 本地 / PyMySQL 预发）
- 覆盖：登录、商品筛选、购物车合并、下单、支付回调、取消订单、库存边界、重复提交、权限校验
- GitHub Actions：push/PR 自动回归，上传 Allure 与 HTML 报告

## 环境变量

- `TEST_ENV`：test / staging（默认 test）
- `ECOM_BASE_URL`：覆盖 base_url
