import json
from commerce_coordinator.apps.commercetools.management.commands._ct_api_client_command import CommercetoolsAPIClientCommand
from commerce_coordinator.apps.commercetools.clients import CTCustomAPIClient

product_id = '21533075-1710-4cbc-88d2-a18ba4176fdd'
product_json = ''' 

{
        "version": 9,
        "actions": [
            {
              "action": "setDescription",
              "description": {
                "en-US": "<p>This course reflects the most current version of the PMP exam, based on the Project Management Institute, Inc's (PMI) current exam content outline (ECO). This will not only prepare you for the PMP, but also teach you valuable project management skills useful for program managers and project managers in this PMP training course.</p><p>Covers PMBOK Guide 7th Edition, PMBOK Guide 6th Edition, Agile Practice Guide, and more. Passing the PMP certification exam is an important step for any individual with project management experience looking to advance their career in the field and wants to earn this valuable credential.  This course covers content related to predictive (traditional), adaptive (Agile), and hybrid projects. Each course allows you to earn up to 10 professional development units (PDUs). When you enroll as a verified learner, you'll have immediate access to study materials for your PMP exam prep.</p><p>This course is taught by Instructor and global keynote speaker, Crystal Richards.  Crystal is an experienced project manager and has over 20 years of experience working with project teams in the private-sector and public-sector. Crystal's client work has been in the healthcare and federal government. She specializes in project management training and is a PMI PMP and PMI-ACP credential holder. Crystal has taught foundational project management courses and project management certification boot camp courses to thousands of students around the world both in the classroom and online.</p><p>The entire course will include the following:<ul><li>Earn 35 PDUs/Contact Hours by completing the entire course as required by PMI</li><li>Content based on the current PMP Examination Content Outline</li><li>Expert guidance completing the PMP application to meet exam eligibility requirements</li><li>Explanation of the project management processes</li><li>Discussion of key project management topics such as scope management, cost management,</li> schedule management, and risk management</li><li>Demonstrate use of key formulas, charts, and graphs</li><li>Strong foundation in Agile project management such as scrum, XP, and Kanban</li><li>Exposure to challenging exam questions on practice exams-including 'wordy' questions, questions with formulas, and questions with more than one correct answer</li><li>Guidance on the logistical details to sit for the exam such as information on the exam fee for PMI members and non-members, paying for PMI membership, prerequisites, and information on test centers.</li></ul></p><p>The course is broken up into 4 modules:<ul><li>PMP Prep: Project Management Principles - This module will provide an overview of predictive, Agile, and hybrid project management methodologies.  The module will also delve into key project roles, and key concepts such as tailoring, progressive elaboration, and rolling wave planning.</li><li>PMP Prep: Managing People with Power Skills - Linked to the Leadership skill area of the PMI Talent Triangle®, this module will place focus on managing the expectations and relationships of the people involved in projects. Participants will need to demonstrate the knowledge, skills and behaviors to guide, motivate and/or direct others to achieve a goal. Key skills related to people include planning resource needs, managing stakeholder expectations, and communications planning and execution.  This module will also delve into 'power skills' such as negotiations, active listening, emotional intelligence, and servant leadership.</li><li>PMP Prep: Determining Ways of Working for Technical Project Management - Linked to the Technical skill area of the PMI Talent Triangle®, this module focuses on the technical aspects of successfully managing projects.  Topics will delve into the core skills of scope, cost, and schedule management and integrating these concepts to develop a master project plan.  Participants will also need to demonstrate an understanding of quality, risk, and procurement management and use techniques such as earned value, critical path methodology, and general data gathering and analysis techniques.</li><li>PMP Prep: Gaining Business Acumen for Project Managers- Linked to the Strategic and Business Management skill area of the PMI Talent Triangle®, this module will highlight the connection between projects and organizational strategy.  Participants will need to demonstrate knowledge of and expertise in the industry/organization, so as to align the project goals and objectives to the organizational goals and enhance performance to better deliver business outcomes.  Additional topics in this module will include compliance management and an understanding of how internal and external factors impact project outcomes.</li></ul></p>"
              }
            },
            {
                "action": "publish"
            }
        ]
    }


'''

class Command(CommercetoolsAPIClientCommand):
    help = "Update a commercetools product from a JSON string or file"

    def handle(self, *args, **options):
        if product_json:
            try:
                product_data = json.loads(product_json)
            except json.JSONDecodeError as e:
                self.stderr.write(f"Invalid JSON format: {e}")
                return
        else:
            print("\n\n\n\nNo JSON data provided.\n\n\n\n")
            return

        version = product_data.get("version")
        actions = product_data.get("actions")

        if not product_id or not version or not actions:
            print("\n\n\n\nMissing product ID, version, or actions.\n\n\n\n")
            return

        # Initialize the custom commercetools client
        ct_client = CTCustomAPIClient()

        # Prepare the data for updating the product
        update_payload = {
            "version": version,
            "actions": actions
        }

        # Make the request to update the product
        endpoint = f"products/{product_id}"
        response = ct_client._make_request(
            method="POST",
            endpoint=endpoint,
            json=update_payload
        )

        if response:
            print(f"\n\n\n\n\nSuccessfully updated product with ID: {response.get('id')}\n\n\n\n\n")
        else:
            print("\n\n\n\n\nError updating product.\n\n\n\n\n\n")
