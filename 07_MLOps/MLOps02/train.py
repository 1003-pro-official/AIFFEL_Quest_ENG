import joblib
from sklearn.datasets import load_iris
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

def train_and_save():
    # 1. 데이터셋 로드
    iris = load_iris()
    X, y = iris.data, iris.target

    # 2. 모델 학습
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = LogisticRegression(max_iter=200)
    model.fit(X_train, y_train)

    score = model.score(X_test, y_test)
    print(f"Model test accuracy: {score:.4f}")

    # 3. 모델 저장
    joblib.dump(model, "model.joblib")
    print("Successfully saved model to model.joblib")

if __name__ == "__main__":
    train_and_save()
