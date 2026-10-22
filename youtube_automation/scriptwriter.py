from .models import Claim, Scene, Script, Topic
from .utils import split_sentences


SPEAKING_RATE_WPS = 2.4


def _scene(scene_id, title, narration, visual, claims=None, min_duration=4.0):
    words = len(narration.split())
    duration = max(min_duration, words / SPEAKING_RATE_WPS + 0.8)
    return Scene(scene_id, title, narration, visual, duration, claims or [])


SAMPLE_SCENES = [
    ("hook", "The Question", "Why does an engine turn fuel into steady motion? Inside a cylinder, a repeating four-stroke cycle transforms chemical energy into mechanical rotation.", "Cutaway cylinder with piston, crankshaft, and four stroke labels; animated arrows show the cycle.", ["claim-1"]),
    ("components", "Main Components", "A four-stroke engine centers on a cylinder, piston, connecting rod, crankshaft, intake and exhaust valves, and an ignition or injection system. The piston moves in a straight line, while the connecting rod and crankshaft convert that motion into rotation.", "Exploded technical drawing of cylinder, piston, connecting rod, crankshaft, valves, and spark plug with labels.", ["claim-2"]),
    ("intake", "Intake Stroke", "During intake, the intake valve opens and the piston moves downward. That motion lowers pressure inside the cylinder and draws in air, or an air-fuel mixture in many older engines. The exhaust valve remains closed.", "Piston moves down; intake valve open; blue arrows show incoming air; exhaust valve closed.", ["claim-3"]),
    ("compression", "Compression Stroke", "Both valves close for compression. The piston moves upward and squeezes the trapped charge into a smaller volume. Higher pressure and temperature prepare the mixture for efficient combustion.", "Piston moves up; both valves closed; compression arrows and pressure labels.", ["claim-4"]),
    ("power", "Power Stroke", "At the top of compression, ignition occurs. A spark plug ignites gasoline mixtures, while diesel engines use heat from compression to ignite injected fuel. Expanding gases force the piston downward and spin the crankshaft. This is the stroke that produces useful power.", "Spark or injection flash; expanding red gas; piston forced down; crankshaft rotates.", ["claim-5"]),
    ("exhaust", "Exhaust Stroke", "The exhaust valve then opens. As the piston moves upward, it pushes burned gases out of the cylinder. Once they leave, the cycle can begin again.", "Exhaust valve open; gray gas flows out; piston moves up.", ["claim-6"]),
    ("timing", "Valve Timing", "A camshaft opens and closes each valve at precise crankshaft angles. Correct timing keeps the cycle efficient; incorrect timing can cause poor running, knocking, overheating, or backfiring.", "Camshaft with lobes, timing marks, and valve lift diagram.", ["claim-7"]),
    ("reliability", "Efficiency and Failure", "Real engines lose energy to heat, friction, pumping losses, and incomplete combustion. Oil films, cooling passages, piston rings, and clean air protect performance. Worn rings, leaking valves, overheating, and detonation are common failure paths.", "Heat and friction arrows, oil film, cooling channels, and failure callouts on the cutaway.", ["claim-7"]),
    ("applications", "Applications and Conclusion", "The same four-stroke principle powers most cars, motorcycles, generators, and many aircraft. Understanding the cycle explains why maintenance matters and why engineers seek better efficiency. The idea is simple; the execution depends on precision.", "Applications montage and final cutaway with all four stroke labels.", ["claim-1"]),
]


def build_script(topic: Topic, research) -> Script:
    if topic.id != "four-stroke-engine":
        raise ValueError("Scriptwriter currently implements the required four-stroke engine sample only")
    scenes = [_scene(sid, title, narration, visual, claims) for sid, title, narration, visual, claims in SAMPLE_SCENES]
    runtime = sum(scene.duration_sec for scene in scenes)
    hook = scenes[0].narration
    conclusion = "The four-stroke cycle converts fuel into motion through intake, compression, power, and exhaust."
    claims = list(research.claims) if research is not None else []
    return Script(topic.id, topic.title, hook, scenes, conclusion, runtime, claims)


def validate_script(script: Script) -> list[str]:
    errors: list[str] = []
    if not script.scenes:
        errors.append("Script has no scenes")
    if script.estimated_runtime_sec > 1200:
        errors.append("Estimated runtime exceeds 20 minutes")
    all_text = " ".join(scene.narration for scene in script.scenes).lower()
    for scene in script.scenes:
        if not scene.visual.strip():
            errors.append(f"Scene {scene.id} has no visual direction")
        if len(scene.narration.split()) < 8:
            errors.append(f"Scene {scene.id} narration is too short")
    # Simple repetition check.
    sentences = split_sentences(all_text)
    seen = set()
    for sentence in sentences:
        key = " ".join(sentence.split()[:8])
        if key in seen and len(key.split()) >= 6:
            errors.append(f"Repeated sentence opening detected: {key}")
        seen.add(key)
    if not script.hook.strip():
        errors.append("Missing hook")
    unsupported = [claim.id for claim in script.claims if claim.status not in {"supported", "uncertain", "unverified"}]
    if unsupported:
        errors.append("Unsupported claims present: " + ", ".join(unsupported))
    return errors
