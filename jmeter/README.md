# JMeter 性能测试

针对电商核心接口的并发压测计划，与 `automation_tests` 功能自动化互补。

## 压测接口

| 接口 | 方法 | 说明 |
|------|------|------|
| /api/auth/login | POST | 用户登录 |
| /api/products | GET | 商品查询 |
| /api/orders | POST | 创建订单 |
| /api/orders | GET | 订单列表 |

## 并发档位

- 50 / 100 / 200 虚拟用户
- Ramp-Up：10 秒
- 循环：10 次

## 关注指标

- 平均响应时间、P90/P95
- 错误率
- 吞吐量 (TPS)

## 运行方式

1. 启动被测服务：`cd ecom_app && uvicorn main:app --port 8000`
2. 打开 JMeter 5.6+
3. 导入 `ecom_load_test.jmx`（或使用 HTTP Request 手动配置）
4. 查看聚合报告 / Summary Report

## 典型发现（面试可讲）

- 商品查询接口在高并发下响应时间波动
- 创建订单接口受库存校验与 DB 写入影响
- 优化方向：分页查询、索引优化、热点缓存
