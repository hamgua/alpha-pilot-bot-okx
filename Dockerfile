# 使用Python 3.11官方镜像作为基础镜像
FROM hamgua/alpha-arena-okx:base_v1.0.1

# 设置时区
ENV TZ=Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs /app/data_json

# 暴露Streamlit端口
EXPOSE 8501

# 健康检查 - 检查Web界面和run.py进程
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health && pgrep -f "python.*run.py" || exit 1

# 统一启动入口
CMD ["python", "-u", "run.py"]

# docker 构建业务镜像命令
# docker buildx build --platform linux/amd64 --no-cache -t hamgua/alpha-arena-okx:v4.4.16 ./
# docker push hamgua/alpha-arena-okx:v4.4.16
