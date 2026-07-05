"""Standalone test harness for the LLM signal (Milestone 3).

Run this to call classify_llm() directly on a few known samples and eyeball the
scores BEFORE the signal is wired into the /submit endpoint.

Usage (from the project root, venv active):
    python scripts/test_llm_signal.py
"""

import sys
from pathlib import Path

# Allow running as a script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from detection.llm_signal import classify_llm

SAMPLES = [
    (
        "Clearly human-written (should score low)",
        "ok so i finally tried that new ramen place downtown and honestly?underwhelming. the broth was fine but they put WAY too much sodium in it and i was thirsty for like three hours after. my friend got the spicy version and said it was better. probably won't go back unless someone drags me there"
    ),
    (
        "Clearly AI-generated (should score high)",
        "Artificial intelligence represents a transformative paradigm shift in modern society. It is important to note that while the benefits of AI are numerous, it is equally essential to consider the ethical implications. Furthermore, stakeholders across various sectors must collaborate to ensure responsible deployment."
    ),
    (
        "Borderline: lightly edited AI output (should ideally score mid-range)",
        "I've been thinking a lot about remote work lately. There are genuine tradeoffs — flexibility and no commute on one side, isolation and blurred work-life boundaries on the other. Studies show productivity varies widely by individual and role type."
    ),
    (

        "AI Sample-1 (should score high)",
        "Artificial Intelligence (AI) has become an important part of everyday life, helping people work more efficiently and solve problems more quickly. AI is used in education to provide personalized learning, in healthcare to assist doctors in diagnosing diseases, in businesses to automate repetitive tasks, and in transportation to improve navigation and safety. It also powers virtual assistants, recommendation systems on streaming platforms, and customer service chatbots. While AI offers many benefits, it should be used responsibly because it can raise concerns about privacy, bias, and job displacement. Overall, AI is a powerful technology that, when used ethically and wisely, can improve productivity, enhance decision-making, and make everyday life more convenient."
    ),
    (
        "AI Sample-2 (should score high)",
        "The global economy in 2026 is being reshaped by rapid technological innovation, changing labor markets, and evolving international trade relationships. Artificial intelligence and automation are transforming industries by increasing productivity while also creating demand for new skills. Many countries are investing in renewable energy, digital infrastructure, and advanced manufacturing to strengthen long-term economic growth. At the same time, businesses and consumers continue to adapt to inflation, shifting interest rates, and changing supply chains. Governments are also focusing on policies that encourage innovation, workforce development, and sustainable growth. As these trends continue, the economy is becoming more technology-driven, interconnected, and focused on resilience in the face of global challenges."
    ),
    (
        "AI Sample-3 (should score high)",
        "A mentor has played a significant role in shaping my career by providing guidance, support, and valuable insights throughout my professional journey. They have helped me identify my strengths, improve my technical and communication skills, and make informed decisions about my education and career goals. Through their encouragement and constructive feedback, I have gained confidence to overcome challenges and pursue new opportunities. A mentor also shares real-world experiences that cannot always be learned in a classroom, helping me develop both professionally and personally. Their advice has inspired me to continue learning, stay focused on my goals, and strive for continuous growth, making them an essential part of my career development."

    ),
    (
        "AI Sample-4 (should score high)",
        "Time management is an essential skill that contributes significantly to academic achievement and personal development. Students who plan their schedules effectively are better able to complete assignments on time, prepare for examinations, and participate in extracurricular activities without becoming overwhelmed. By setting priorities and breaking large tasks into smaller, manageable goals, students can reduce stress while improving the quality of their work. Furthermore, effective time management encourages self-discipline, responsibility, and consistency, which are valuable qualities in both academic and professional environments."\
        ""
        "In addition to improving academic performance, time management promotes a healthier balance between education and personal life. Students who organize their time efficiently are more likely to maintain regular sleep schedules, engage in physical activities, and spend meaningful time with family and friends. These habits contribute to better mental and physical well-being, enabling students to remain motivated and productive throughout their studies. Therefore, developing strong time management skills is not only beneficial for achieving academic success but also for building lifelong habits that support personal growth and future career success."
    ),
    (
        "Human Sample-1 (should score low)",
        "British Cycling changed one day in 2003. The organization, which was the governing body for professional cycling in Great Britain, had recently hired Dave Brailsford as its new performance director. At the time, professional cyclists in Great Britain had endured nearly one hundred years of mediocrity. Since 1908, British riders had won just a single gold medal at the Olympic Games, and they had fared even worse in cycling’s biggest race, the Tour de France. In 110 years, no British cyclist had ever won the event. In fact, the performance of British riders had been so underwhelming that one of the top bike manufacturers in Europe refused to sell bikes to the team because they were afraid that it would hurt sales if other professionals saw the Brits using their gear."
    ),
    (
        "Human Sample-2 (should score low)",
        " All right, I’m going to do it. I’m going to write an essay about Star Trek" \
        "" \
        "I hope you haven’t read many Star Trek essays before this one. They tend to" \
        "be formulaic, lauding Trek’s vision of a brighter, better future, its daring in" \
        "employing a multiethnic cast, its inspiring mission “to boldly go”... I think" \
        "all that stuff is cool too, but everything about it has already been said, and" \
        "I don’t want to add to the mountain of pages already written on those" \
        "subjects. I’ll attempt to come up with something marginally more original" \
        "by discussing a different facet of Trek, one that has had a larger impact on" \
        "me personally." \
        "" \
        "I understand that you may have never seen an episode of Star Trek in your" \
        "life. You may be thinking, “Isn’t that the one with the guy with the funny" \
        "ears?” You may be thinking, “Isn’t that the one with that Yoda guy?”," \
        "but I hope not. (That’s Star Wars, by the by.) I’m going to talk about the" \
        "people with the “funny ears,” people who I think are rather neat. They’re" \
        "called Vulcans, and they live according to a philosophy called IDIC. (Aha! I" \
        "remember that word from the title! But what does it mean?) "
    ),
    (
        "Human Sample-3 (should score low)",
        "There was always one group of individuals that demanded the most respect in my family—teachers. Truth be told, my mother has worked as an elementary and middle school teacher my whole life. My father is an adjunct instructor at our local community college. My brother and I were taught from an early age that all teachers were the ultimate role models."\
        ""
        "Once I graduated high school, I started to realize that my parents were onto something. Sure, there were things I needed to learn when I got to college.  But I arrived at college with important lessons about integrity, character, and fairness from my teachers back home that grounded me during trying times. I learned from them how a silly little passion of mine like public speaking could turn into my biggest strength as a professional. That’s the power of a teacher." 
    ),
    (
        "Human Sample-4 (should score low)",
        "Shortly after I got the book, my family visited the New York City Museum of Natural History, and, as fate would have it, the butterfly exhibit was open. I was so ecstatic that I could barely stand it. When I walked into the lush green jungle, my eyes lit up like a Christmas tree; I pointed out different species and twirled around, taking it all in. One of the workers welcomed us and described the rules of the exhibit, but my eyes were fixated on a display case depicting metamorphosis. I pointed to the case and blurted out, “Chrysalis!” She looked at me in awe, utterly astounded that a toddler could identify a chrysalis. She asked me to follow her to see something special. “Put out your hand,” she whispered, and a gorgeous yellow swallowtail floated down and perched on my finger. People stopped to gather around me and observe with reverence and amazement. Most three-year-olds probably would’ve crushed the delicate insect, but I stood as still as a statue with my jaw hanging open. I watched its intricate wings flap back and forth like rustling leaves in a morning breeze. After fourteen years, that day is still imbedded in my memory. For me, it represents the first moment when my passion for learning allowed me to find deep meaning in the simplest creature."
    )
]


def main():
    for label, text in SAMPLES:
        print("=" * 70)
        print(f"SAMPLE: {label}")
        print(f"TEXT:   {text[:80]}{'...' if len(text) > 80 else ''}")
        result = classify_llm(text)
        print(f"  llm_score : {result['llm_score']}  (0=human, 1=AI)")
        print(f"  reason    : {result['reason']}")
    print("=" * 70)


if __name__ == "__main__":
    main()
