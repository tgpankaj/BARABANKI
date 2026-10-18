import re
from datetime import timedelta
from app.core.database import SessionLocal, init_db, utc_now
from app.core.security import get_password_hash
from app.models import (
    User,
    UserFollow,
    NewsArticle,
    Event,
    EventRegistration,
    Business,
    JobListing,
    EducationInstitute,
    CommunityPost,
    Comment,
    TourismSpot,
    CreatorProfile,
    CivicIssue,
    CivicIssueUpvote,
    IssueStatusHistory,
    Notification,
)



def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def seed():
    """Populate database with verified Barabanki baseline data and clearly labelled demo items."""
    init_db()
    db = SessionLocal()

    try:
        # 1. Seed Users if not already present
        admin_user = db.query(User).filter(User.email == "admin@barabanki.local").first()
        if not admin_user:
            admin_user = User(
                username="admin",
                email="admin@barabanki.local",
                hashed_password=get_password_hash("Admin@123456"),
                full_name="Barabanki Admin",
                phone="+91-5248-222001",
                role="admin",
                bio="Chief Administrator for the Barabanki Connect Community Portal.",
                is_active=True,
            )
            db.add(admin_user)

        mod_user = db.query(User).filter(User.email == "moderator@barabanki.local").first()
        if not mod_user:
            mod_user = User(
                username="moderator",
                email="moderator@barabanki.local",
                hashed_password=get_password_hash("Moderator@123456"),
                full_name="Civic Moderator",
                phone="+91-5248-222002",
                role="moderator",
                bio="Community guidelines enforcer and local content moderator.",
                is_active=True,
            )
            db.add(mod_user)

        citizen_user = db.query(User).filter(User.email == "citizen@barabanki.local").first()
        if not citizen_user:
            citizen_user = User(
                username="aarav_sharma",
                email="citizen@barabanki.local",
                hashed_password=get_password_hash("Citizen@123456"),
                full_name="Aarav Sharma",
                phone="+91-9876543210",
                role="resident",
                bio="B.Tech IT student and passionate technology explorer from Barabanki.",
                is_active=True,
            )
            db.add(citizen_user)

        artisan_user = db.query(User).filter(User.email == "artisan@barabanki.local").first()
        if not artisan_user:
            artisan_user = User(
                username="mohd_rafiq",
                email="artisan@barabanki.local",
                hashed_password=get_password_hash("Artisan@123456"),
                full_name="Mohammad Rafiq Ansari",
                phone="+91-9839001122",
                role="creator",
                bio="3rd generation Jacquard and Handloom weaver from Zaidpur, Barabanki.",
                is_active=True,
            )
            db.add(artisan_user)

        db.commit()
        db.refresh(admin_user)
        db.refresh(citizen_user)
        db.refresh(artisan_user)

        # 2. Seed Creator Profile
        if not db.query(CreatorProfile).filter(CreatorProfile.user_id == artisan_user.id).first():
            creator = CreatorProfile(
                user_id=artisan_user.id,
                title="Master Jacquard & Silk Weaver",
                craft_category="Handloom & Textiles",
                bio="Preserving the centuries-old handloom legacy of Zaidpur. Crafting high-count cotton stoles, linen scarves, and brocade yardages using traditional wooden frame looms.",
                skills="Jacquard Looms, Natural Dyeing, Traditional Motifs, Warp Sizing",
                portfolio_url="https://zaidpurweaves.example.in",
                instagram="@zaidpur_handlooms",
                is_featured=True,
            )
            db.add(creator)

        # 3. Seed Tourism & Heritage Spots
        tourism_data = [
            {
                "name": "Deva Sharif (Shrine of Haji Waris Ali Shah)",
                "category": "Spiritual & Shrines",
                "short_description": "The sacred Sufi shrine preaching universal brotherhood ('Jo Rab Hai Wahi Ram Hai') and host to the historic annual Deva Mela.",
                "historical_background": "Deva Sharif is the tomb and birthplace of Hazrat Waris Ali Shah (1819–1905), a revered saint who had disciples across all faiths and backgrounds. The monument features exquisite Indo-Islamic marble architecture with intricate lattice stone carvings, attracting millions of spiritual seekers during the month of Safar.",
                "visiting_hours": "Open 24 hours daily (Shrine sanctum: 04:00 AM - 10:30 PM)",
                "entry_fee": "Free Entry",
                "nearest_railway_station": "Barabanki Junction (12 km) / Lucknow Charbagh (40 km)",
                "distance_from_headquarters": "12 km North of Nawabganj",
                "address": "Deva Sharif, Tehsil Nawabganj, Barabanki, Uttar Pradesh 225301",
                "locality": "Deva",
                "latitude": 27.0223,
                "longitude": 81.1685,
                "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=800&q=80",
                "best_time_to_visit": "October to March (Special during Deva Mela in Oct/Nov)",
            },
            {
                "name": "Parijaat Sacred Tree (Kintoor)",
                "category": "Botanical Wonders & Heritage",
                "short_description": "A legendary celestial baobab tree considered sacred across India, botanically unique with ancient folklore tracing back to the Mahabharata.",
                "historical_background": "Located in village Kintoor (named after Kunti, mother of the Pandavas), this ancient female-sterile tree produces fragrant white-yellow blossoms at night that turn golden in dawn sunlight. In Indian lore, Lord Krishna brought it from Indra's swarga garden. Botanists categorize it as an exceptionally rare, protected Adansonia digitata specimen.",
                "visiting_hours": "06:00 AM - 07:00 PM daily",
                "entry_fee": "Free Entry",
                "nearest_railway_station": "Barabanki Junction (38 km)",
                "distance_from_headquarters": "38 km East of District HQ",
                "address": "Village Kintoor, Block Baddupur, Barabanki, Uttar Pradesh 225203",
                "locality": "Kintoor",
                "latitude": 27.0425,
                "longitude": 81.4795,
                "image_url": "https://images.unsplash.com/photo-1502082553048-f009c37129b9?auto=format&fit=crop&w=800&q=80",
                "best_time_to_visit": "August to December",
            },
            {
                "name": "Lodheshwar Mahadev Temple (Mahadeva)",
                "category": "Ancient Heritage & Shrines",
                "short_description": "One of the most sacred Shiva pilgrimage centers in Awadh, drawing hundreds of thousands of Kanwariyas every Mahashivratri.",
                "historical_background": "Situated in Ramnagar tehsil along the historic banks of the Ghaghara river, this ancient shrine enshrines an extraordinarily old Swayambhu Shivalinga associated with the Pandava era during their exile in the forest. It remains one of the five prominent Shiva seats in Uttar Pradesh.",
                "visiting_hours": "04:30 AM - 09:30 PM daily",
                "entry_fee": "Free Entry",
                "nearest_railway_station": "Burhwal Junction (6 km) / Barabanki (28 km)",
                "distance_from_headquarters": "28 km North-East of Nawabganj",
                "address": "Mahadeva, Tehsil Ramnagar, Barabanki, Uttar Pradesh 225205",
                "locality": "Ramnagar",
                "latitude": 27.1852,
                "longitude": 81.4011,
                "image_url": "https://images.unsplash.com/photo-1609766857041-ed402ea8069a?auto=format&fit=crop&w=800&q=80",
                "best_time_to_visit": "February to March & July/August (Shravan)",
            },
            {
                "name": "Barabanki Clock Tower (Ghanta Ghar)",
                "category": "Architecture & Civic Heritage",
                "short_description": "Colonial-era architectural clock tower that marks the historical center of the Nawabganj municipality.",
                "historical_background": "Erected in the early 20th century, the Barabanki Clock Tower stands as an iconic civic landmark witnessing the growth of the town from a bustling Awadhi market into a thriving educational and regional commerce district.",
                "visiting_hours": "Public open viewing at all times",
                "entry_fee": "Free Entry",
                "nearest_railway_station": "Barabanki Junction (1.5 km)",
                "distance_from_headquarters": "0.5 km (City Center)",
                "address": "Clock Tower Chauraha, Nawabganj Market, Barabanki, Uttar Pradesh 225001",
                "locality": "Nawabganj",
                "latitude": 26.9288,
                "longitude": 81.1895,
                "image_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
                "best_time_to_visit": "All year round",
            },
        ]

        for item in tourism_data:
            slug = slugify(item["name"])
            if not db.query(TourismSpot).filter(TourismSpot.slug == slug).first():
                spot = TourismSpot(**item, slug=slug)
                db.add(spot)

        # 4. Seed Education Institutes
        education_data = [
            {
                "name": "Jahangirabad National University / Institute of Technology (JNT)",
                "category": "College",
                "affiliation": "Dr. A.P.J. Abdul Kalam Technical University (AKTU) & BTEUP",
                "address": "Jahangirabad Fort, Tehsil Nawabganj, Barabanki, UP 225203",
                "locality": "Jahangirabad",
                "phone": "+91-5248-262100",
                "email": "admissions@jit.edu.in",
                "website": "https://jit.edu.in",
                "description": "Situated within the historical Jahangirabad Fort, this institution provides higher technical education across Computer Science, Information Technology, Mechanical, and Civil Engineering with modern labs.",
                "courses_offered": "B.Tech (CS, IT, ME, CE), Polytechnic Diploma, MBA, BCA, Media Studies",
                "admission_info": "Admissions via UPSEE / CUET and merit-based institutional counseling.",
            },
            {
                "name": "Sagar Institute of Technology & Management (SITM)",
                "category": "College",
                "affiliation": "Dr. A.P.J. Abdul Kalam Technical University (AKTU) & PCI",
                "address": "Lucknow-Ayodhya National Highway, Barabanki, UP 225001",
                "locality": "Barabanki Highway",
                "phone": "+91-5248-228300",
                "email": "info@sagar.edu.in",
                "website": "https://sitm.edu.in",
                "description": "A premier technical and pharmaceutical education campus located strategically along the Lucknow-Ayodhya highway, equipped with high-performance computing centers and placement support.",
                "courses_offered": "B.Tech in Computer Science, B.Pharm, D.Pharm, MBA, M.Tech",
                "admission_info": "Direct counseling and state-level JEE / CUET admission quotas.",
            },
            {
                "name": "Government Polytechnic Barabanki",
                "category": "Polytechnic / ITI",
                "affiliation": "Board of Technical Education Uttar Pradesh (BTEUP)",
                "address": "Near District Jail Road, Nawabganj, Barabanki, UP 225001",
                "locality": "Nawabganj",
                "phone": "+91-5248-224510",
                "email": "polytechnicbbk@gmail.com",
                "website": "https://bteup.ac.in",
                "description": "State-run technical diploma institute empowering local students with hands-on vocational engineering skills and industrial apprentice workshops.",
                "courses_offered": "Diploma in Electronics Engineering, Computer Application, Mechanical Engineering",
                "admission_info": "Joint Entrance Examination Council Uttar Pradesh (JEECUP).",
            },
            {
                "name": "Jawahar Navodaya Vidyalaya, Sonikpur",
                "category": "School",
                "affiliation": "Central Board of Secondary Education (CBSE)",
                "address": "Sonikpur, Post Baddupur, Barabanki, UP 225203",
                "locality": "Sonikpur",
                "phone": "+91-5248-241020",
                "email": "jnvbarabanki@gmail.com",
                "website": "https://navodaya.gov.in",
                "description": "Co-educational premier residential school managed by Navodaya Vidyalaya Samiti, dedicated to nurturing talented rural children with complete boarding and academic excellence.",
                "courses_offered": "Class 6 to Class 12 (Science, Commerce, Arts Streams)",
                "admission_info": "JNVST (Jawahar Navodaya Vidyalaya Selection Test) for Class 6 and 9.",
            },
            {
                "name": "Lakshya Career & Civil Services Coaching Academy",
                "category": "Coaching Centre",
                "affiliation": "Registered Educational Academy",
                "address": "Civil Lines, Opposite Head Post Office, Barabanki, UP 225001",
                "locality": "Nawabganj",
                "phone": "+91-9415002233",
                "email": "contact@lakshyabbk.in",
                "website": "https://lakshyabbk.example.in",
                "description": "Dedicated preparatory institute mentoring Barabanki youth for UP Police, SSC, UPSSSC PET, Railway, and state competitive examinations.",
                "courses_offered": "UPSSSC PET, UP Police Constable & SI, SSC CGL/CHSL Foundation, General Studies",
                "admission_info": "Monthly weekend and regular morning/evening batches.",
            },
        ]

        for item in education_data:
            slug = slugify(item["name"])
            if not db.query(EducationInstitute).filter(EducationInstitute.slug == slug).first():
                inst = EducationInstitute(**item, slug=slug)
                db.add(inst)

        # 5. Seed Local Businesses (Demonstration entries marked clearly)
        business_data = [
            {
                "name": "Zaidpur Handloom Weavers Producer Society",
                "category": "Handloom & Textiles",
                "description": "Artisan-owned collective producing authentic hand-woven cotton stoles, dupattas, linen shawls, and Jacquard furnishings directly from Zaidpur loom sheds.",
                "address": "Main Bunkar Colony, Zaidpur, Barabanki, UP 225414",
                "locality": "Zaidpur",
                "phone": "+91-9839123456",
                "email": "contact@zaidpurweaves.example.in",
                "website": "https://zaidpurweaves.example.in",
                "opening_hours": "09:00 AM - 07:00 PM",
                "latitude": 26.8333,
                "longitude": 81.3333,
                "rating": 4.9,
                "is_verified": True,
                "is_demo": False,
            },
            {
                "name": "Kalyani Agro & Peppermint (Mentha) Processing",
                "category": "Agro & Fertilizers",
                "description": "Specialized procurement and steam-distillation center for Mentha arvensis (peppermint oil), quality testing, and agricultural inputs for regional farmers.",
                "address": "Haidergarh Road Industrial Area, Barabanki, UP 225126",
                "locality": "Haidergarh",
                "phone": "+91-9450998877",
                "email": "kalyaniagro@example.com",
                "website": "https://kalyaniagro.example.com",
                "opening_hours": "08:00 AM - 06:00 PM",
                "latitude": 26.6022,
                "longitude": 81.2501,
                "rating": 4.7,
                "is_verified": True,
                "is_demo": False,
            },
            {
                "name": "Shree Ram Sweets & Restaurant",
                "category": "Dining & Sweets",
                "description": "Celebrated heritage confectioners known for fresh desi ghee sweets, Makkhan Malai, Jalebi, and authentic vegetarian meals in Nawabganj.",
                "address": "Near Clock Tower, Civil Lines, Nawabganj, Barabanki, UP 225001",
                "locality": "Nawabganj",
                "phone": "+91-5248-223400",
                "email": "info@shreeramsweets.example.com",
                "website": "https://shreeramsweets.example.com",
                "opening_hours": "07:30 AM - 10:30 PM",
                "latitude": 26.9290,
                "longitude": 81.1890,
                "rating": 4.8,
                "is_verified": True,
                "is_demo": True,
            },
            {
                "name": "Apex Diagnostic & Poly Clinic",
                "category": "Healthcare",
                "description": "Comprehensive diagnostic pathology, digital X-Ray, ultrasound, and multispecialty doctor consultations serving Barabanki residents.",
                "address": "Opposite District Hospital Gate, Nawabganj, Barabanki, UP 225001",
                "locality": "Nawabganj",
                "phone": "+91-5248-226789",
                "email": "care@apexclinic.example.com",
                "website": "https://apexclinic.example.com",
                "opening_hours": "08:00 AM - 09:00 PM (Emergency 24x7)",
                "latitude": 26.9320,
                "longitude": 81.1840,
                "rating": 4.6,
                "is_verified": True,
                "is_demo": True,
            },
        ]

        for item in business_data:
            slug = slugify(item["name"])
            if not db.query(Business).filter(Business.slug == slug).first():
                biz = Business(**item, slug=slug, created_by_id=admin_user.id)
                db.add(biz)

        # 6. Seed News Articles (With explicit source attribution)
        news_data = [
            {
                "title": "District Administration Reviews Deva Mela Preparations and Pilgrim Facilities",
                "summary": "District Magistrate convenes inter-departmental review meeting for security, sanitation, unhindered electricity, and transport coordination for the upcoming historic Deva Mela.",
                "content": "The Barabanki District Administration held a high-level coordination meeting at the Deva Sharif pilgrim complex to review readiness ahead of the annual Urs and fair. Key directives issued include round-the-clock medical camps, temporary roadways bus services from Barabanki Junction and Charbagh, high-definition CCTV monitoring, and dedicated citizen helpdesks. Sanitation teams have been instructed to ensure daily deep cleaning of the mela grounds and surrounding approaches.",
                "category": "Administration",
                "source_attribution": "District Information Office (DIO), Barabanki Civic Bulletin",
                "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=800&q=80",
                "views_count": 342,
            },
            {
                "title": "UP Skill Development Mission Launches Free IT & AI Training Batches in Barabanki",
                "summary": "Unemployed youth and college graduates can now enroll in certified full-stack web development and data literacy programs at local IT centres.",
                "content": "In an effort to expand digital career avenues for rural and suburban youth, the District Skill Development Cell announced the commencement of five free vocational batches in Barabanki. The curriculum covers foundational programming, responsive web design, digital accounting, and modern office productivity. Interested candidates between 18 and 35 years can register with their Aadhaar and educational certificates.",
                "category": "Education",
                "source_attribution": "Uttar Pradesh Skill Development Mission (UPSDM) Press Release",
                "image_url": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=800&q=80",
                "views_count": 512,
            },
            {
                "title": "Modernization of Barabanki Junction Under Amrit Bharat Station Scheme Advances",
                "summary": "Passenger amenities, modern concourse, improved circulating areas, and disabled-friendly escalators are nearing completion at Barabanki Junction.",
                "content": "Northern Railway officials inspected the ongoing redevelopment work at Barabanki Junction railway station. Upgrades include a newly designed facade reflecting Awadhi cultural motifs, an upgraded waiting lounge, energy-efficient LED illumination, automated ticket vending kiosks, and an expansive 12-meter-wide foot overbridge connecting all platforms seamlessly.",
                "category": "Development",
                "source_attribution": "Northern Railway Public Relations Bureau",
                "image_url": "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=800&q=80",
                "views_count": 420,
            },
            {
                "title": "KVK Barabanki Issues Advisory for Mentha and Rabi Crop Protection Following Weather Shift",
                "summary": "Agricultural scientists advise farmers on optimal irrigation intervals and pest surveillance for peppermint and winter vegetable crops.",
                "content": "Krishi Vigyan Kendra (KVK) Barabanki has issued a timely advisory for farmers cultivating peppermint, mustard, and seasonal vegetables across Haidergarh, Ramnagar, and Fatehpur tehsils. Farmers are urged to monitor for early blight and utilize biological neem-based formulations, while scheduling drip or light sprinkler irrigation during morning hours.",
                "category": "Agro",
                "source_attribution": "Krishi Vigyan Kendra (ICAR), Barabanki Research Unit",
                "image_url": "https://images.unsplash.com/photo-1500937386664-56d1dfef3854?auto=format&fit=crop&w=800&q=80",
                "views_count": 288,
            },
        ]

        for item in news_data:
            slug = slugify(item["title"])
            if not db.query(NewsArticle).filter(NewsArticle.slug == slug).first():
                art = NewsArticle(**item, slug=slug, author_id=admin_user.id)
                db.add(art)

        # 7. Seed Events
        now = utc_now()
        event_data = [
            {
                "title": "Barabanki Annual Deva Mela & Cultural Festival",
                "description": "The world-famous historic festival featuring All-India Mushaira, Kavi Sammelan, musical performances, agricultural exhibits, and cattle shows at the sacred grounds of Deva Sharif.",
                "category": "Cultural",
                "start_date": now + timedelta(days=15),
                "end_date": now + timedelta(days=25),
                "venue_name": "Deva Sharif Mela Ground",
                "address": "Deva Sharif, Barabanki, UP 225301",
                "locality": "Deva",
                "latitude": 27.0223,
                "longitude": 81.1685,
                "organizer_name": "Deva Mela Committee & District Administration",
                "organizer_contact": "+91-5248-222001",
                "registration_link": "https://barabanki.nic.in/deva-mela",
                "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "District Youth Tech & Employment Summit 2026",
                "description": "One-day conference connecting IT graduates, engineering diploma holders, and local enterprises for on-the-spot interviews, resume reviews, and startup pitching.",
                "category": "Educational",
                "start_date": now + timedelta(days=7, hours=9),
                "end_date": now + timedelta(days=7, hours=17),
                "venue_name": "Auditorium, JNT Campus",
                "address": "Jahangirabad Fort Road, Barabanki, UP",
                "locality": "Jahangirabad",
                "latitude": 26.9800,
                "longitude": 81.2500,
                "organizer_name": "Barabanki Youth & Innovation Forum",
                "organizer_contact": "connect@barabanki.local",
                "registration_link": "#rsvp",
                "image_url": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Traditional Zaidpur Handloom Weavers Expo",
                "description": "Exhibition and direct sale of handwoven stoles, bed linens, dupattas, and natural dyed fabrics directly from local master craftspeople.",
                "category": "Exhibition",
                "start_date": now + timedelta(days=20),
                "end_date": now + timedelta(days=24),
                "venue_name": "Municipal Town Hall Grounds, Nawabganj",
                "address": "Near Ghanta Ghar, Nawabganj, Barabanki",
                "locality": "Nawabganj",
                "latitude": 26.9288,
                "longitude": 81.1895,
                "organizer_name": "Barabanki Handloom Weavers Cluster",
                "organizer_contact": "+91-9839123456",
                "registration_link": None,
                "image_url": "https://images.unsplash.com/photo-1607344645866-009c320c5ab8?auto=format&fit=crop&w=800&q=80",
            },
        ]

        for item in event_data:
            slug = slugify(item["title"])
            if not db.query(Event).filter(Event.slug == slug).first():
                evt = Event(**item, slug=slug)
                db.add(evt)

        # 8. Seed Job Listings (Demonstration vacancies clearly noted)
        job_data = [
            {
                "title": "Junior Python / Web Developer",
                "company_name": "Awadh SoftTech Solutions (Demo Employer)",
                "job_type": "Full-time",
                "category": "IT & Tech",
                "location": "Nawabganj, Barabanki / Hybrid",
                "salary_range": "₹22,000 - ₹35,000 / month",
                "description": "Looking for an energetic junior developer with knowledge of Python, HTML, CSS, JavaScript, and SQL to assist in building civic and commercial web applications for local clients.",
                "requirements": "B.Tech IT/CS or BCA degree; understanding of REST APIs; Git fundamentals; good problem-solving ability.",
                "application_email": "careers@awadhsoft.example.com",
                "application_link": "https://awadhsoft.example.com/apply",
                "is_demo": True,
            },
            {
                "title": "Textile Quality Control Supervisor",
                "company_name": "Zaidpur Handloom Exports",
                "job_type": "Full-time",
                "category": "Manufacturing",
                "location": "Zaidpur Cluster, Barabanki",
                "salary_range": "₹18,000 - ₹26,000 / month",
                "description": "Responsible for inspecting yarn counts, reed-pick consistency, colorfastness, and packaging of handloom stoles and fabrics prior to dispatch.",
                "requirements": "Diploma in Textile Technology / Handloom Weaving or 2+ years field experience in weaving inspection.",
                "application_email": "hr@zaidpuroverseas.example.com",
                "is_demo": True,
            },
            {
                "title": "High School Mathematics & Science Tutor",
                "company_name": "Adarsh Vidyalaya (Demo School)",
                "job_type": "Part-time",
                "category": "Education",
                "location": "Ramnagar, Barabanki",
                "salary_range": "₹12,000 - ₹18,000 / month",
                "description": "Engage Classes 8 to 10 in mathematics and basic science with clear conceptual demonstrations and test series mentorship.",
                "requirements": "B.Sc (Maths/Physics) or B.Ed; fluent Hindi and English explanation skills; patient demeanor.",
                "application_email": "principal@adarshschool.example.com",
                "is_demo": True,
            },
        ]

        for item in job_data:
            slug = slugify(item["title"] + " " + item["company_name"])
            if not db.query(JobListing).filter(JobListing.slug == slug).first():
                job = JobListing(**item, slug=slug, posted_by_id=admin_user.id)
                db.add(job)

        # 9. Seed Community Posts & Comments
        post_data = [
            {
                "title": "How can we make public transit between Nawabganj and Deva Sharif more commuter-friendly?",
                "content": "Every day hundreds of students and daily office-goers commute between Nawabganj city and Deva Sharif. While e-rickshaws and shared tempos exist, having scheduled electric minibuses with fixed stops could drastically cut down congestion and travel time. What do other residents think?",
                "category": "Civic Issue",
                "upvotes": 18,
            },
            {
                "title": "Tips for first-year engineering and IT diploma students in Barabanki",
                "content": "Welcome to all new students enrolling at JNT, SITM, and Govt Polytechnic! Make sure to set up your GitHub account early, build real web projects instead of just memorizing syntax, and participate in open-source hackathons. Let's build a vibrant student developer circle right here in Barabanki!",
                "category": "Student Hub",
                "upvotes": 24,
            },
            {
                "title": "Supporting local handloom weavers: Where can we buy authentic Zaidpur scarves locally?",
                "content": "Instead of ordering synthetic scarves online, I recently visited the artisan sheds in Zaidpur and was blown away by the craftsmanship. We should establish a weekend artisan bazaar in Nawabganj Clock Tower square to connect weavers directly with city buyers.",
                "category": "Discussion",
                "upvotes": 31,
            },
        ]

        for item in post_data:
            slug = slugify(item["title"])
            existing_post = db.query(CommunityPost).filter(CommunityPost.slug == slug).first()
            if not existing_post:
                post = CommunityPost(
                    **item,
                    slug=slug,
                    author_id=citizen_user.id,
                )
                db.add(post)
                db.flush()

                # Add a realistic comment
                comment = Comment(
                    post_id=post.id,
                    author_id=admin_user.id,
                    content="Great civic suggestion! The municipal council and transport department are currently surveying high-density feeder routes for electric minibus trials.",
                )
                db.add(comment)

        # 10. Seed Follow Relationships if not present
        if citizen_user and artisan_user:
            existing_follow = db.query(UserFollow).filter(UserFollow.follower_id == citizen_user.id, UserFollow.following_id == artisan_user.id).first()
            if not existing_follow:
                db.add(UserFollow(follower_id=citizen_user.id, following_id=artisan_user.id))
            admin_follow = db.query(UserFollow).filter(UserFollow.follower_id == admin_user.id, UserFollow.following_id == artisan_user.id).first()
            if not admin_follow:
                db.add(UserFollow(follower_id=admin_user.id, following_id=artisan_user.id))

        # 11. Seed Baseline Civic Issues (Screen 8)
        civic_issues_data = [
            {
                "title": "Severe potholes and waterlogging near Railway Colony crossing",
                "category": "Roads & Potholes",
                "locality": "Barabanki City",
                "landmark": "Opposite Railway Colony Gate 2",
                "description": "Monsoon rains have caused deep craters on the main feeder lane. Two-wheelers frequently slip during night hours. Immediate gravel patch and drainage desilting required.",
                "image_url": "https://images.unsplash.com/photo-1515162816999-a0c47dc192f7?w=800&q=80",
                "status": "In Progress",
                "upvotes": 18,
            },
            {
                "title": "Malfunctioning solar streetlights on Deva Road bypass stretch",
                "category": "Streetlights",
                "locality": "Deva Sharif",
                "landmark": "Near Canal Bridge turning",
                "description": "Six streetlights along the pilgrim bypass road have remained dark for over ten days, creating pedestrian hazards during evening prayer hours.",
                "image_url": "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=800&q=80",
                "status": "Under Review",
                "upvotes": 12,
            },
            {
                "title": "Overflowing community waste bin near Subzi Mandi entrance",
                "category": "Sanitation & Garbage",
                "locality": "Nawabganj",
                "landmark": "Subzi Mandi main square",
                "description": "Municipal bin requires daily morning collection; currently overflowing onto the footpath attracting stray cattle. Sanitization drive needed.",
                "image_url": None,
                "status": "Resolved",
                "upvotes": 25,
            },
        ]

        for item in civic_issues_data:
            iss_slug = slugify(item["title"])
            existing_issue = db.query(CivicIssue).filter(CivicIssue.slug == iss_slug).first()
            if not existing_issue:
                issue = CivicIssue(
                    **item,
                    slug=iss_slug,
                    reported_by_id=citizen_user.id,
                )
                db.add(issue)
                db.flush()

                # Status History
                hist = IssueStatusHistory(
                    issue_id=issue.id,
                    old_status="None",
                    new_status="Submitted",
                    notes="Citizen grievance logged with digital geotag.",
                    changed_by_id=citizen_user.id,
                )
                db.add(hist)
                if item["status"] != "Submitted":
                    hist2 = IssueStatusHistory(
                        issue_id=issue.id,
                        old_status="Submitted",
                        new_status=item["status"],
                        notes="Assigned to municipal inspection cell.",
                        changed_by_id=mod_user.id,
                    )
                    db.add(hist2)

                # Upvote
                db.add(CivicIssueUpvote(issue_id=issue.id, user_id=citizen_user.id))

        # 12. Seed Event Registration & Capacity
        first_event = db.query(Event).filter(Event.is_approved == True).first()
        if first_event:
            first_event.capacity = 250
            existing_reg = db.query(EventRegistration).filter(EventRegistration.event_id == first_event.id, EventRegistration.user_id == citizen_user.id).first()
            if not existing_reg:
                db.add(EventRegistration(
                    event_id=first_event.id,
                    user_id=citizen_user.id,
                    status="confirmed",
                    notes="Attending with local youth club delegation",
                ))

        # 13. Seed Baseline Notification
        existing_notif = db.query(Notification).filter(Notification.recipient_id == citizen_user.id).first()
        if not existing_notif:
            db.add(Notification(
                recipient_id=citizen_user.id,
                sender_id=admin_user.id,
                notification_type="issue_status",
                title="Welcome to Barabanki Connect",
                message="Your citizen account is verified. You can report civic problems, register for local events, and participate in community discussions.",
                link="/issues",
                is_read=False,
            ))

        db.commit()
        print("Barabanki Connect seed data successfully created!")


    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
