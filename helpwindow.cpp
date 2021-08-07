/*
    Drumstick MIDI File Player Multiplatform Program
    Copyright (C) 2006-2021, Pedro Lopez-Cabanillas <plcl@users.sf.net>

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
*/

#include <QApplication>
#include <QWindow>
#include <QScreen>
#include <QHBoxLayout>
#include <QVBoxLayout>

#include <drumstick/settingsfactory.h>
#include "settings.h"
#include "iconutils.h"
#include "helpwindow.h"

HelpWindow::HelpWindow(const QString &path, const QString &page, QWidget *parent):
    QWidget(parent)
{
    setAttribute(Qt::WA_DeleteOnClose);
    setWindowIcon(QIcon(":/dmidiplayer.png"));

    textBrowser = new QTextBrowser(this);
    homeButton = new QPushButton(tr("&Home"), this);
    homeButton->setIcon(IconUtils::GetIcon("go-home"));
    backButton = new QPushButton(tr("&Back"), this);
    backButton->setIcon(IconUtils::GetIcon("go-previous"));
    closeButton = new QPushButton(tr("Close"), this);
    closeButton->setShortcut(tr("Esc"));
    closeButton->setIcon(IconUtils::GetIcon("window-close"));

    QHBoxLayout *buttonLayout = new QHBoxLayout;
    buttonLayout->addWidget(homeButton);
    buttonLayout->addWidget(backButton);
    buttonLayout->addStretch();
    buttonLayout->addWidget(closeButton);

    QVBoxLayout *mainLayout = new QVBoxLayout(this);
    mainLayout->addLayout(buttonLayout);
    mainLayout->addWidget(textBrowser);
    setLayout(mainLayout);

    connect(homeButton, &QAbstractButton::clicked, textBrowser, &QTextBrowser::home);
    connect(backButton, &QAbstractButton::clicked, textBrowser, &QTextBrowser::backward);
    connect(closeButton, &QAbstractButton::clicked, this, &QWidget::close);
    connect(textBrowser, &QTextBrowser::sourceChanged, this, &HelpWindow::updateWindowTitle);

    QPalette p = textBrowser->palette();
    p.setColor(QPalette::Base, Qt::white);
    p.setColor(QPalette::Text, Qt::black);
    textBrowser->setPalette(p);

    textBrowser->setSearchPaths(QStringList({path,":/help",":/help/en"}));
    textBrowser->setSource(page);
    textBrowser->setOpenExternalLinks(true);

    resize(640,480);
    readSettings();
    retranslateUi();
#if defined(Q_OS_WINDOWS)
    m_snapper.SetEnabled(Settings::instance()->winSnap());
#endif
}

void HelpWindow::readSettings()
{
    using namespace drumstick::widgets;
    SettingsFactory settings;
    settings->beginGroup("HelpWindow");
    restoreGeometry(settings->value("Geometry").toByteArray());
    settings->endGroup();
}

void HelpWindow::writeSettings()
{
    using namespace drumstick::widgets;
    SettingsFactory settings;
    settings->beginGroup("HelpWindow");
    settings->setValue("Geometry", saveGeometry());
    settings->endGroup();
}


void HelpWindow::closeEvent(QCloseEvent *event)
{
    writeSettings();
    event->accept();
}

bool HelpWindow::nativeEvent(const QByteArray &eventType, void *message,
 #if QT_VERSION < QT_VERSION_CHECK(6,0,0)
                          long *result
 #else
                          qintptr *result
 #endif
                         )
{
#if defined(Q_OS_WINDOWS)
    if (m_snapper.HandleMessage(message)) {
        result = 0;
        return true;
    }
#endif
    return QWidget::nativeEvent(eventType, message, result);
}

void HelpWindow::updateWindowTitle()
{
    setWindowTitle(tr("Help: %1").arg(textBrowser->documentTitle()));
}

void HelpWindow::showPage(const QString &page)
{
    HelpWindow *browser = new HelpWindow(QLatin1String(":/"), page);
    browser->show();
}

void HelpWindow::retranslateUi()
{
    updateWindowTitle();
    homeButton->setText(tr("&Home"));
    backButton->setText(tr("&Back"));
    closeButton->setText(tr("Close"));
    closeButton->setShortcut(tr("Esc"));
}