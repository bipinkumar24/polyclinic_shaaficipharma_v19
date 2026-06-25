# -*- coding: utf-8 -*-
#╔══════════════════════════════════════════════════════════════════════╗
#║                                                                      ║
#║                  ╔═══╦╗       ╔╗  ╔╗     ╔═══╦═══╗                   ║
#║                  ║╔═╗║║       ║║ ╔╝╚╗    ║╔═╗║╔═╗║                   ║
#║                  ║║ ║║║╔╗╔╦╦══╣╚═╬╗╔╬╗ ╔╗║║ ╚╣╚══╗                   ║
#║                  ║╚═╝║║║╚╝╠╣╔╗║╔╗║║║║║ ║║║║ ╔╬══╗║                   ║
#║                  ║╔═╗║╚╣║║║║╚╝║║║║║╚╣╚═╝║║╚═╝║╚═╝║                   ║
#║                  ╚╝ ╚╩═╩╩╩╩╩═╗╠╝╚╝╚═╩═╗╔╝╚═══╩═══╝                   ║
#║                            ╔═╝║     ╔═╝║                             ║
#║                            ╚══╝     ╚══╝                             ║
#║                  SOFTWARE DEVELOPED AND SUPPORTED BY                 ║
#║                ALMIGHTY CONSULTING SOLUTIONS PVT. LTD.               ║
#║                      COPYRIGHT (C) 2016 - TODAY                      ║
#║                      https://www.almightycs.com                      ║
#║                                                                      ║
#╚══════════════════════════════════════════════════════════════════════╝
{
    'name': 'Certificate Management System',
    'summary': """This Module will Add functionality to provide certificate to Customers, Vendors, Employees and Users. Maintain history of certificate allocation.""",
    'description': """
        This Module will Add functionality to provide certificate to Customers, Vendors, Employees and Users. Maintain history of certificate allocation.
        Certification User Certification Employee Certification Employee Certificate Product Warranty Certificate

        Este módulo agregará funcionalidad para proporcionar certificados a clientes, proveedores, empleados y usuarios. Mantener el historial de asignación de certificados.
         Certificación de usuario Certificación Certificación de empleado Certificado de empleado Producto Certificado de garantía
        
        Ce module ajoutera une fonctionnalité permettant de fournir un certificat aux clients, aux fournisseurs, aux employés et aux utilisateurs. Conserver l'historique de l'attribution des certificats.
         Certification Utilisateur Certification Certificat d'employé Certificat d'employé Certificat de garantie de produit

        Dieses Modul fügt Funktionalität hinzu, um Kunden, Lieferanten, Mitarbeitern und Benutzern ein Zertifikat bereitzustellen. Verwalten Sie den Verlauf der Zertifikatszuteilung.
         Zertifizierung Benutzerzertifizierung Mitarbeiterzertifikat Mitarbeiterzertifikat Produktgarantiezertifikat
    """,
    'version': '19.0.1.0.0',
    'category': 'Extra Addons',
    'author': 'Almighty Consulting Solutions Pvt. Ltd.',
    'support': 'info@almightycs.com',
    'website': 'https://www.almightycs.com',
    'license': 'OPL-1',
    'depends': ["mail", "digest", "portal"],
    'data' : [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'data/digest_data.xml',
        'views/certificate_management_view.xml',
        'views/digest_view.xml',
        'report/certificate_report.xml',
        'views/portal_template.xml',
        'views/menu_item.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'images': [
        'static/description/acs_certificate_almightycs_cover.jpg',
    ],
    'installable': True,
    'application': True,
    'sequence': 1,
    'price': 35,
    'currency': 'USD',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: