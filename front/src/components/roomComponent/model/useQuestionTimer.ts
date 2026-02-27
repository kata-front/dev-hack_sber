import { useEffect, useMemo, useState } from 'react'

type UseQuestionTimerParams = {
  isGameActive: boolean
  activeQuestionIndex: number
  hasAnswerStatus: boolean
  serverCounter?: number
  questionDurationSeconds: number
  isPaused: boolean
}

type LocalTimerState = {
  questionIndex: number
  timeLeft: number
}

const clampToNonNegative = (value: number) => (value < 0 ? 0 : value)

export const useQuestionTimer = ({
  isGameActive,
  activeQuestionIndex,
  hasAnswerStatus,
  serverCounter,
  questionDurationSeconds,
  isPaused,
}: UseQuestionTimerParams) => {
  const [localTimer, setLocalTimer] = useState<LocalTimerState>({
    questionIndex: activeQuestionIndex,
    timeLeft: questionDurationSeconds,
  })

  const localTimeLeft =
    localTimer.questionIndex === activeQuestionIndex
      ? localTimer.timeLeft
      : questionDurationSeconds

  const hasServerCounter = typeof serverCounter === 'number' && serverCounter > 0
  const isLocalTimerRunning =
    isGameActive && activeQuestionIndex > 0 && !hasAnswerStatus && !isPaused && !hasServerCounter

  useEffect(() => {
    if (!isLocalTimerRunning) return

    const timer = setInterval(() => {
      setLocalTimer((prev) => {
        const scopedTime =
          prev.questionIndex === activeQuestionIndex ? prev.timeLeft : questionDurationSeconds

        return {
          questionIndex: activeQuestionIndex,
          timeLeft: clampToNonNegative(scopedTime - 1),
        }
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [isLocalTimerRunning, activeQuestionIndex, questionDurationSeconds])

  const effective = useMemo(() => {
    if (!isGameActive || !activeQuestionIndex) {
      return clampToNonNegative(localTimeLeft)
    }

    if (isPaused) {
      return clampToNonNegative(
        typeof serverCounter === 'number' ? serverCounter : localTimeLeft
      )
    }

    if (hasAnswerStatus) {
      return clampToNonNegative(localTimeLeft)
    }

    if (hasServerCounter) {
      return clampToNonNegative(serverCounter)
    }

    return clampToNonNegative(localTimeLeft)
  }, [
    isGameActive,
    activeQuestionIndex,
    isPaused,
    serverCounter,
    localTimeLeft,
    hasAnswerStatus,
    hasServerCounter,
  ])

  return {
    timeLeft: effective,
    isServerSynced: hasServerCounter,
  }
}
